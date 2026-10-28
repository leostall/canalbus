"""Três extensões fora de src/, importando apenas a API pública."""

from canalbus import (
    DispatchStrategy, Message, MessageBusBuilder, MessageValidator,
    Receiver, Subscription,
)


class RequiredMetadataValidator(MessageValidator):
    """Exige uma chave nos metadados, sem modificar a mensagem."""

    def __init__(self, key: str) -> None:
        super().__init__()
        self._key = key

    def check(self, message: Message) -> str | None:
        if self._key not in message.metadata:
            return f"Metadado obrigatório ausente: {self._key}."
        return None


class FirstSubscriberStrategy(DispatchStrategy):
    """Seleciona apenas o primeiro inscrito, sem manter cursor."""

    def select(
        self, message: Message, subscriptions: tuple[Subscription, ...]
    ) -> tuple[Subscription, ...]:
        return subscriptions[:1]


class CountingReceiver(Receiver):
    """Mantém uma contagem, sem depender do CollectingReceiver."""

    def __init__(self) -> None:
        self.count = 0

    def receive(self, message: Message) -> None:
        self.count += 1


def main() -> None:
    bus = (
        MessageBusBuilder()
        .with_strategy(FirstSubscriberStrategy)
        .add_validator(lambda: RequiredMetadataValidator("origem"))
        .build()
    )
    first, second = CountingReceiver(), CountingReceiver()
    bus.subscribe("producao", first)
    bus.subscribe("producao", second)
    rejected = bus.publish("producao", "Lote sem origem")
    accepted = bus.publish("producao", "Lote identificado", {"origem": "linha-1"})
    assert not rejected.accepted and accepted.accepted
    assert first.count == 1 and second.count == 0
    print("Rejeição:", rejected.rejection_reason)
    print(f"Contagem dos receptores personalizados: {first.count}, {second.count}")


if __name__ == "__main__":
    main()
