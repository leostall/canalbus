"""Adapter: uma função existente participa sem implementar uma classe."""

from canalbus import CallbackReceiverAdapter, Message, MessageBus


def main() -> None:
    received: list[str] = []

    def register_event(message: Message) -> None:
        received.append(message.content)

    bus = MessageBus()

    bus.subscribe("manutencao", CallbackReceiverAdapter(register_event))

    result = bus.publish("manutencao", "Sensor revisado, mas precisará de trocas em 6 meses.")

    assert received == ["Sensor revisado, mas precisará de trocas em 6 meses."] and result.deliveries[0].succeeded

    print("Função adaptada recebeu:", received[0])


if __name__ == "__main__":
    main()