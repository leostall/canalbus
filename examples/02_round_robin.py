"""Strategy: alternância independente por canal."""

from canalbus import CollectingReceiver, MessageBusBuilder, RoundRobinStrategy


def main() -> None:
    bus = MessageBusBuilder().with_strategy(RoundRobinStrategy).build()

    first_receptor, second_receptor = CollectingReceiver(), CollectingReceiver()

    for channel in ("producao", "manutencao"):
        bus.subscribe(channel, first_receptor)
        bus.subscribe(channel, second_receptor)

    for channel, content in (
        ("producao", "Produção recebendo a primeira mensagem"), ("producao", "Produção recebendo a segunda mensagem"),
        ("manutencao", "Manutenção recebendo a primeira mensagem"), ("producao", "Produção recebendo a terceira mensagem"),
    ):
        bus.publish(channel, content)
    
    assert [message.content for message in first_receptor.messages] == ["Produção recebendo a primeira mensagem", "Manutenção recebendo a primeira mensagem", "Produção recebendo a terceira mensagem"]
    assert [message.content for message in second_receptor.messages] == ["Produção recebendo a segunda mensagem"]

    print("Receptor 1:", [message.content for message in first_receptor.messages])
    print("Receptor 2:", [message.content for message in second_receptor.messages])


if __name__ == "__main__":
    main()

