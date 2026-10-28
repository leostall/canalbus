"""Strategy: alternância independente por canal."""

from canalbus import CollectingReceiver, MessageBusBuilder, RoundRobinStrategy


def main() -> None:
    bus = MessageBusBuilder().with_strategy(RoundRobinStrategy).build()
    first, second = CollectingReceiver(), CollectingReceiver()
    for channel in ("producao", "manutencao"):
        bus.subscribe(channel, first)
        bus.subscribe(channel, second)
    for channel, content in (
        ("producao", "P1"), ("producao", "P2"),
        ("manutencao", "M1"), ("producao", "P3"),
    ):
        bus.publish(channel, content)
    assert [message.content for message in first.messages] == ["P1", "M1", "P3"]
    assert [message.content for message in second.messages] == ["P2"]
    print("Receptor 1:", [message.content for message in first.messages])
    print("Receptor 2:", [message.content for message in second.messages])


if __name__ == "__main__":
    main()

