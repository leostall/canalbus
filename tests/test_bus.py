import pytest

from canalbus import (
    CallbackReceiverAdapter, CollectingReceiver, ExecutionMode, MessageBus,
    MessageBusBuilder, Receiver, RoundRobinStrategy,
)


def test_default_broadcast_and_individual_results():
    bus = MessageBus()
    receivers = [CollectingReceiver() for _ in range(3)]
    ids = [bus.subscribe("a", receiver) for receiver in receivers]
    result = bus.publish("a", "texto")
    assert result.accepted and result.rejection_reason is None
    assert result.queued_count == 0 and result.selected_count == 3
    assert [delivery.subscription_id for delivery in result.deliveries] == ids
    for receiver, delivery in zip(receivers, result.deliveries):
        assert receiver.messages == (result.message,)
        assert delivery.message_id == result.message.id and delivery.succeeded
        assert delivery.error_type is None and delivery.error_message is None
    assert bus.pending_count == 0
    assert bus.process_pending().processed_count == 0


def test_duplicate_instance_and_removal():
    bus = MessageBus()
    receiver = CollectingReceiver()
    original = bus.subscribe(" a ", receiver)
    assert bus.subscribe("a", receiver) == original
    assert bus.publish("a", "primeira").selected_count == 1
    assert bus.unsubscribe(original)
    assert not bus.unsubscribe(original)
    assert not bus.unsubscribe("inexistente")
    assert bus.publish("a", "segunda").selected_count == 0
    assert len(receiver.messages) == 1
    assert bus.subscribe("a", receiver) != original


def test_deduplication_uses_identity_not_equality():
    class EqualReceiver(CollectingReceiver):
        def __eq__(self, other):
            return True

    bus = MessageBus()
    first, second = EqualReceiver(), EqualReceiver()
    assert bus.subscribe("a", first) != bus.subscribe("a", second)
    assert bus.publish("a", "texto").selected_count == 2
    assert len(first.messages) == len(second.messages) == 1


def test_same_receiver_across_channels_and_case_sensitivity():
    bus = MessageBus()
    receiver = CollectingReceiver()
    first = bus.subscribe(" a ", receiver)
    second = bus.subscribe("A", receiver)
    assert first != second
    bus.publish("a", "minúsculo")
    bus.publish(" A ", "maiúsculo")
    assert [message.channel for message in receiver.messages] == ["a", "A"]


@pytest.mark.parametrize("mode", list(ExecutionMode))
def test_valid_publication_without_subscribers_is_accepted(mode):
    result = MessageBus(mode=mode).publish("vazio", "texto")
    assert result.accepted
    assert result.selected_count == result.queued_count == 0
    assert result.deliveries == ()


def test_receiver_failure_does_not_block_other_receivers():
    def fail(message):
        raise RuntimeError("receptor indisponível")

    bus = MessageBus()
    collector = CollectingReceiver()
    failing_id = bus.subscribe("a", CallbackReceiverAdapter(fail))
    bus.subscribe("a", collector)
    result = bus.publish("a", "texto")
    assert result.accepted
    assert [delivery.succeeded for delivery in result.deliveries] == [False, True]
    failure = result.deliveries[0]
    assert failure.subscription_id == failing_id
    assert failure.error_type == "RuntimeError"
    assert failure.error_message == "receptor indisponível"
    assert collector.messages == (result.message,)


def test_immediate_delivery_uses_snapshot_even_when_receiver_changes_subscriptions():
    bus = MessageBus()
    original, newcomer = CollectingReceiver(), CollectingReceiver()

    def change(message):
        bus.unsubscribe(original_id)
        bus.subscribe("a", newcomer)

    bus.subscribe("a", CallbackReceiverAdapter(change))
    original_id = bus.subscribe("a", original)
    bus.publish("a", "primeira")
    assert len(original.messages) == 1 and newcomer.messages == ()
    bus.publish("a", "segunda")
    assert len(original.messages) == len(newcomer.messages) == 1


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_delivery_does_not_swallow_base_exception(error_type):
    def interrupt(message):
        raise error_type()

    bus = MessageBus()
    bus.subscribe("a", CallbackReceiverAdapter(interrupt))
    with pytest.raises(error_type):
        bus.publish("a", "texto")


def test_round_robin_independent_channels_and_invalid_publications():
    bus = MessageBusBuilder().with_strategy(RoundRobinStrategy).build()
    first, second = CollectingReceiver(), CollectingReceiver()
    for channel in ("a", "b"):
        bus.subscribe(channel, first)
        bus.subscribe(channel, second)
    bus.publish("a", "a1")
    assert not bus.publish("a", " ").accepted
    bus.publish("a", "a2")
    bus.publish("b", "b1")
    bus.publish("a", "a3")
    bus.publish("b", "b2")
    assert [message.content for message in first.messages] == ["a1", "b1", "a3"]
    assert [message.content for message in second.messages] == ["a2", "b2"]


def test_round_robin_changes_use_positional_cursor_and_reset_on_empty_publish():
    bus = MessageBusBuilder().with_strategy(RoundRobinStrategy).build()
    first, second, third = (CollectingReceiver() for _ in range(3))
    ids = [bus.subscribe("a", receiver) for receiver in (first, second, third)]
    assert bus.publish("a", "1").deliveries[0].subscription_id == ids[0]
    bus.unsubscribe(ids[0])
    assert bus.publish("a", "2").deliveries[0].subscription_id == ids[2]
    bus.unsubscribe(ids[2])
    assert bus.publish("a", "3").deliveries[0].subscription_id == ids[1]
    new_id = bus.subscribe("a", first)
    assert bus.publish("a", "4").deliveries[0].subscription_id == new_id
    bus.unsubscribe(ids[1])
    bus.unsubscribe(new_id)
    assert bus.publish("a", "vazio").selected_count == 0
    restart_id = bus.subscribe("a", second)
    bus.subscribe("a", third)
    assert bus.publish("a", "reinício").deliveries[0].subscription_id == restart_id


@pytest.mark.parametrize("receiver", [None, object(), lambda message: None])
def test_invalid_receiver(receiver):
    with pytest.raises(TypeError):
        MessageBus().subscribe("a", receiver)


def test_invalid_subscription_id():
    with pytest.raises(TypeError):
        MessageBus().unsubscribe(None)


def test_receiver_contract_requires_implementation():
    with pytest.raises(TypeError):
        Receiver()

