"""Chain of Responsibility: regras padrão e uma regra externa de liberação."""

from canalbus import CollectingReceiver, Message, MessageBusBuilder, MessageValidator


class ReleasedLotValidator(MessageValidator):
    """Só aprova lotes explicitamente liberados pela aplicação cliente."""

    def check(self, message: Message) -> str | None:
        if message.metadata.get("liberado") is not True:
            return "O lote precisa estar liberado antes da publicação."
        return None


def main() -> None:
    bus = (
        MessageBusBuilder()
        .with_max_length(40)
        .add_validator(ReleasedLotValidator)
        .build()
    )
    receiver = CollectingReceiver()
    bus.subscribe("producao", receiver)

    # Sem liberação, estas mensagens também violam a regra externa. Mesmo assim,
    # o resultado é a primeira rejeição da cadeia: vazio -> tamanho -> liberação.
    empty = bus.publish("producao", "   ")
    too_long = bus.publish("producao", "x" * 41)
    not_released = bus.publish("producao", "Lote 42 concluído", {"liberado": False})

    assert empty.rejection_reason == "O conteúdo não pode ser vazio ou conter apenas espaços."
    assert too_long.rejection_reason == "O conteúdo excede o limite de 40 caracteres."
    assert not_released.rejection_reason == "O lote precisa estar liberado antes da publicação."
    for result in (empty, too_long, not_released):
        assert not result.accepted and result.selected_count == 0
        assert result.deliveries == () and result.queued_count == 0
        print("Rejeitada:", result.rejection_reason)
    assert receiver.messages == ()

    accepted = bus.publish("producao", "Lote 42 concluído", {"liberado": True})
    assert accepted.accepted and accepted.rejection_reason is None
    assert len(accepted.deliveries) == 1 and accepted.deliveries[0].succeeded
    assert receiver.messages == (accepted.message,)
    print("Aprovada e entregue:", receiver.messages[0].content)


if __name__ == "__main__":
    main()
