import pytest

from canalbus import (
    CallbackReceiverAdapter, CollectingReceiver, DeliverMessageCommand, Message,
    MessageBus, Subscription, TimingReceiverDecorator,
)


def test_callback_adapter_delivers_message():
    messages = []
    bus = MessageBus()
    bus.subscribe("a", CallbackReceiverAdapter(messages.append))
    result = bus.publish("a", "texto")
    assert messages == [result.message] and result.deliveries[0].succeeded


@pytest.mark.parametrize("callback", [None, 42, "funcao", object()])
def test_adapter_rejects_noncallable(callback):
    with pytest.raises(TypeError):
        CallbackReceiverAdapter(callback)


def test_timing_success_and_immutable_measurement_snapshot():
    collector = CollectingReceiver()
    timed = TimingReceiverDecorator(collector)
    bus = MessageBus()
    bus.subscribe("a", timed)
    initial = timed.measurements
    result = bus.publish("a", "texto")
    assert initial == ()
    measurement = timed.measurements[0]
    assert measurement.message_id == result.message.id
    assert measurement.duration_seconds >= 0 and measurement.succeeded
    assert collector.messages == (result.message,)
    assert isinstance(timed.measurements, tuple)


def test_timing_records_failure_and_preserves_original_exception():
    failure = ValueError("original")

    def fail(message):
        raise failure

    timed = TimingReceiverDecorator(CallbackReceiverAdapter(fail))
    message = Message("a", "texto")
    with pytest.raises(ValueError) as raised:
        timed.receive(message)
    assert raised.value is failure
    assert not timed.measurements[0].succeeded
    assert timed.measurements[0].duration_seconds >= 0
    result = DeliverMessageCommand(message, Subscription("a", timed)).execute()
    assert not result.succeeded and result.error_message == "original"
    assert len(timed.measurements) == 2


def test_decorators_can_be_nested():
    collector = CollectingReceiver()
    inner = TimingReceiverDecorator(collector)
    outer = TimingReceiverDecorator(inner)
    message = Message("a", "texto")
    outer.receive(message)
    assert collector.messages == (message,)
    assert inner.measurements[0].succeeded and outer.measurements[0].succeeded


def test_decorator_rejects_invalid_receiver():
    with pytest.raises(TypeError):
        TimingReceiverDecorator(lambda message: None)


def test_production_code_does_not_print(capsys):
    bus = MessageBus()
    bus.subscribe("a", TimingReceiverDecorator(CollectingReceiver()))
    bus.publish("a", "texto")
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""

