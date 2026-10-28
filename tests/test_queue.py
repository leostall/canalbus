import pytest

from canalbus import (
    CallbackReceiverAdapter, CollectingReceiver, ExecutionMode, MessageBus,
    MessageBusBuilder,
)


def queued_bus():
    return MessageBusBuilder().with_execution_mode(ExecutionMode.QUEUED).build()


def test_fifo_order_partial_processing_and_delivery_identifiers():
    received = []
    bus = queued_bus()
    first_id = bus.subscribe("a", CallbackReceiverAdapter(lambda message: received.append(("first", message.content))))
    second_id = bus.subscribe("a", CallbackReceiverAdapter(lambda message: received.append(("second", message.content))))
    first = bus.publish("a", "1")
    second = bus.publish("a", "2")
    assert first.accepted and first.queued_count == 2
    assert first.deliveries == () and received == [] and bus.pending_count == 4
    partial = bus.process_pending(limit=3)
    assert received == [("first", "1"), ("second", "1"), ("first", "2")]
    assert partial.processed_count == 3 and partial.remaining_count == 1
    assert [(item.message_id, item.subscription_id) for item in partial.deliveries] == [
        (first.message.id, first_id), (first.message.id, second_id), (second.message.id, first_id)
    ]
    final = bus.process_pending(limit=10)
    assert final.processed_count == 1 and final.remaining_count == 0
    assert received[-1] == ("second", "2")
    assert bus.process_pending().deliveries == ()


def test_queued_recipients_survive_unsubscribe_and_ignore_new_subscriptions():
    bus = queued_bus()
    old, new = CollectingReceiver(), CollectingReceiver()
    old_id = bus.subscribe("a", old)
    result = bus.publish("a", "antiga")
    assert bus.unsubscribe(old_id)
    bus.subscribe("a", new)
    processing = bus.process_pending()
    assert processing.deliveries[0].subscription_id == old_id
    assert old.messages == (result.message,) and new.messages == ()


@pytest.mark.parametrize("limit", [None, 100])
def test_new_commands_during_processing_wait_for_next_call(limit):
    bus = queued_bus()
    received = []

    def republish(message):
        received.append(message.content)
        if message.content == "original":
            bus.publish("a", "gerada")

    bus.subscribe("a", CallbackReceiverAdapter(republish))
    bus.publish("a", "original")
    bus.publish("a", "já pendente")
    first = bus.process_pending(limit)
    assert first.processed_count == 2 and first.remaining_count == 1
    assert received == ["original", "já pendente"]
    bus.process_pending()
    assert received == ["original", "já pendente", "gerada"]


def test_failure_is_recorded_removed_and_never_retried():
    calls = []

    def fail(message):
        calls.append(message.id)
        raise ValueError("falha esperada")

    bus = queued_bus()
    collector = CollectingReceiver()
    bus.subscribe("a", CallbackReceiverAdapter(fail))
    bus.subscribe("a", collector)
    result = bus.publish("a", "texto")
    processing = bus.process_pending()
    assert [item.succeeded for item in processing.deliveries] == [False, True]
    assert processing.deliveries[0].error_type == "ValueError"
    assert processing.remaining_count == 0 and calls == [result.message.id]
    assert collector.messages == (result.message,)
    bus.process_pending()
    assert calls == [result.message.id]


@pytest.mark.parametrize("mode", list(ExecutionMode))
@pytest.mark.parametrize("limit, error", [(0, ValueError), (-1, ValueError), (True, TypeError), (1.5, TypeError), ("1", TypeError)])
def test_invalid_processing_limits(mode, limit, error):
    with pytest.raises(error):
        MessageBus(mode=mode).process_pending(limit)


def test_rejected_message_does_not_enqueue_or_change_existing_queue():
    bus = queued_bus()
    bus.subscribe("a", CollectingReceiver())
    bus.publish("a", "válida")
    result = bus.publish("a", " ")
    assert not result.accepted and result.queued_count == 0
    assert bus.pending_count == 1


def test_reentrant_processing_is_rejected_and_outer_queue_continues():
    bus = queued_bus()
    collector = CollectingReceiver()
    recursive_id = bus.subscribe("a", CallbackReceiverAdapter(lambda message: bus.process_pending()))
    bus.subscribe("a", collector)
    bus.publish("a", "primeira")
    processing = bus.process_pending()
    assert [item.succeeded for item in processing.deliveries] == [False, True]
    assert processing.deliveries[0].error_type == "RuntimeError"
    bus.unsubscribe(recursive_id)
    bus.publish("a", "segunda")
    assert bus.process_pending().deliveries[0].succeeded
    assert len(collector.messages) == 2


def test_base_exception_leaves_remaining_commands_and_resets_processing_guard():
    bus = queued_bus()

    def interrupt(message):
        raise KeyboardInterrupt()

    collector = CollectingReceiver()
    bus.subscribe("a", CallbackReceiverAdapter(interrupt))
    bus.subscribe("a", collector)
    bus.publish("a", "texto")
    with pytest.raises(KeyboardInterrupt):
        bus.process_pending()
    assert bus.pending_count == 1
    assert bus.process_pending().deliveries[0].succeeded
    assert len(collector.messages) == 1


def test_metadata_snapshot_survives_mutation_before_processing():
    bus = queued_bus()
    receiver = CollectingReceiver()
    bus.subscribe("a", receiver)
    source = {"origem": "original"}
    bus.publish("a", "texto", source)
    source["origem"] = "alterada"
    bus.process_pending()
    assert receiver.messages[0].metadata["origem"] == "original"

