import pytest

from canalbus import (
    CollectingReceiver, DispatchStrategy, ExecutionMode, MaxLengthValidator,
    Message, MessageBus, MessageBusBuilder, MessageValidator,
    NonEmptyContentValidator, RoundRobinStrategy, Subscription,
)


@pytest.mark.parametrize("content", ["", " ", "\t\n"])
def test_empty_content_rejected(content):
    bus = MessageBus()
    receiver = CollectingReceiver()
    bus.subscribe("a", receiver)
    result = bus.publish("a", content)
    assert not result.accepted and result.rejection_reason
    assert result.selected_count == 0 and receiver.messages == ()
    assert result.message.content == content


def test_default_size_boundary_and_configured_limit():
    default = MessageBus()
    assert default.publish("a", "x" * 1000).accepted
    assert not default.publish("a", "x" * 1001).accepted
    configured = MessageBusBuilder().with_max_length(3).build()
    assert configured.publish("a", " x ").accepted
    assert not configured.publish("a", " x  ").accepted


def test_chain_order_short_circuit_and_defaults_before_extensions():
    calls = []

    class RecordingValidator(MessageValidator):
        def __init__(self, name, reason=None):
            super().__init__()
            self.name, self.reason = name, reason

        def check(self, message):
            calls.append(self.name)
            return self.reason

    bus = (
        MessageBusBuilder().with_max_length(4)
        .add_validator(lambda: RecordingValidator("first"))
        .add_validator(lambda: RecordingValidator("second", "bloqueada"))
        .add_validator(lambda: RecordingValidator("third"))
        .build()
    )
    assert not bus.publish("a", " ").accepted
    assert not bus.publish("a", "longo").accepted
    assert calls == []
    result = bus.publish("a", "ok")
    assert result.rejection_reason == "bloqueada"
    assert calls == ["first", "second"]


def test_custom_validator_and_validation_before_subscription_snapshot():
    bus = None
    receiver = CollectingReceiver()

    class SubscribeOnValidation(MessageValidator):
        def check(self, message):
            if "origem" not in message.metadata:
                return "origem obrigatória"
            bus.subscribe(message.channel, receiver)
            return None

    bus = MessageBusBuilder().add_validator(SubscribeOnValidation).build()
    assert not bus.publish("a", "texto").accepted
    result = bus.publish("a", "texto", {"origem": "teste"})
    assert result.accepted and receiver.messages == (result.message,)


@pytest.mark.parametrize("value, error", [(0, ValueError), (-1, ValueError), (True, TypeError), (1.5, TypeError), ("2", TypeError), (None, TypeError)])
def test_invalid_length_configuration(value, error):
    with pytest.raises(error):
        MaxLengthValidator(value)
    with pytest.raises(error):
        MessageBusBuilder().with_max_length(value)


def test_chain_rejects_cycles():
    first, second = NonEmptyContentValidator(), MaxLengthValidator()
    first.set_next(second)
    with pytest.raises(ValueError):
        second.set_next(first)
    with pytest.raises(ValueError):
        first.set_next(first)


@pytest.mark.parametrize("reason", ["", "  ", False, 42])
def test_invalid_custom_validation_result_is_programming_error(reason):
    class InvalidValidator(MessageValidator):
        def check(self, message):
            return reason

    bus = MessageBusBuilder().add_validator(InvalidValidator).build()
    with pytest.raises(TypeError):
        bus.publish("a", "texto")


def test_builder_reuse_isolates_queue_registry_strategy_and_validator_state():
    class OnceValidator(MessageValidator):
        def __init__(self):
            super().__init__()
            self.used = False

        def check(self, message):
            if self.used:
                return "já utilizado"
            self.used = True
            return None

    builder = (
        MessageBusBuilder().with_strategy(RoundRobinStrategy)
        .with_execution_mode(ExecutionMode.QUEUED).add_validator(OnceValidator)
    )
    first_bus, second_bus = builder.build(), builder.build()
    first_receivers = [CollectingReceiver(), CollectingReceiver()]
    second_receivers = [CollectingReceiver(), CollectingReceiver()]
    for bus, receivers in ((first_bus, first_receivers), (second_bus, second_receivers)):
        for receiver in receivers:
            bus.subscribe("a", receiver)
    assert first_bus.publish("a", "primeira").queued_count == 1
    assert second_bus.pending_count == 0
    assert second_bus.publish("a", "segunda").queued_count == 1
    first_bus.process_pending()
    assert second_bus.pending_count == 1
    second_bus.process_pending()
    assert len(first_receivers[0].messages) == len(second_receivers[0].messages) == 1
    assert first_receivers[1].messages == second_receivers[1].messages == ()
    assert not first_bus.publish("a", "repetida").accepted
    assert not second_bus.publish("a", "repetida").accepted


def test_default_instances_and_builder_reconfiguration_are_independent():
    first, second = MessageBus(), MessageBus()
    receiver = CollectingReceiver()
    first.subscribe("a", receiver)
    assert second.publish("a", "texto").selected_count == 0
    builder = MessageBusBuilder()
    original = builder.build()
    changed = builder.with_max_length(2).with_execution_mode(ExecutionMode.QUEUED).build()
    assert original.publish("a", "longo").accepted
    assert not changed.publish("a", "longo").accepted


def test_invalid_configuration_contracts():
    for kwargs in ({"mode": "queued"}, {"strategy": object()}, {"validator": object()}):
        with pytest.raises(TypeError):
            MessageBus(**kwargs)
    with pytest.raises(TypeError):
        MessageBusBuilder().with_execution_mode("queued")
    with pytest.raises(TypeError):
        MessageBusBuilder().with_strategy(RoundRobinStrategy())
    with pytest.raises(TypeError):
        MessageBusBuilder().add_validator(None)
    with pytest.raises(TypeError):
        MessageBusBuilder().with_strategy(lambda: object()).build()
    with pytest.raises(TypeError):
        MessageBusBuilder().add_validator(lambda: object()).build()


def test_builder_requires_distinct_unlinked_validation_nodes():
    first = NonEmptyContentValidator()
    first.set_next(MaxLengthValidator())
    with pytest.raises(ValueError):
        MessageBusBuilder().add_validator(lambda: first).build()
    single = NonEmptyContentValidator()
    with pytest.raises(ValueError):
        MessageBusBuilder().add_validator(lambda: single).add_validator(lambda: single).build()


@pytest.mark.parametrize("invalid_kind", ["list", "duplicate", "foreign"])
def test_strategy_must_select_valid_snapshot_subscriptions(invalid_kind):
    class InvalidStrategy(DispatchStrategy):
        def select(self, message, subscriptions):
            if invalid_kind == "list":
                return list(subscriptions)
            if invalid_kind == "duplicate":
                return (subscriptions[0], subscriptions[0])
            return (Subscription(message.channel, CollectingReceiver()),)

    bus = MessageBusBuilder().with_strategy(InvalidStrategy).build()
    receiver = CollectingReceiver()
    bus.subscribe("a", receiver)
    with pytest.raises(TypeError if invalid_kind == "list" else ValueError):
        bus.publish("a", "texto")
    assert receiver.messages == ()


def test_extension_exception_propagates_without_delivery():
    class BrokenValidator(MessageValidator):
        def check(self, message):
            raise RuntimeError("erro na regra")

    bus = MessageBusBuilder().add_validator(BrokenValidator).build()
    receiver = CollectingReceiver()
    bus.subscribe("a", receiver)
    with pytest.raises(RuntimeError, match="erro na regra"):
        bus.publish("a", "texto")
    assert receiver.messages == ()
