"""Decorator: medições em sucesso e falha, sem sleep ou impressão no núcleo."""

from canalbus import (
    CallbackReceiverAdapter, CollectingReceiver, Message, MessageBus,
    TimingReceiverDecorator,
)


def main() -> None:
    def fail(message: Message) -> None:
        raise RuntimeError("Falha demonstrativa do receptor")

    successful = TimingReceiverDecorator(CollectingReceiver())
    failing = TimingReceiverDecorator(CallbackReceiverAdapter(fail))
    bus = MessageBus()
    bus.subscribe("producao", failing)
    bus.subscribe("producao", successful)
    result = bus.publish("producao", "Medir entrega")
    assert [item.succeeded for item in result.deliveries] == [False, True]
    assert not failing.measurements[0].succeeded
    assert successful.measurements[0].succeeded
    for name, receiver in (("Falha", failing), ("Sucesso", successful)):
        measurement = receiver.measurements[0]
        print(f"{name}: {measurement.duration_seconds:.8f} segundos")


if __name__ == "__main__":
    main()

