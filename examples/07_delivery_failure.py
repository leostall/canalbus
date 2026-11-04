"""Uma falha de entrega é registrada sem impedir os próximos receptores."""

from canalbus import CallbackReceiverAdapter, CollectingReceiver, Message, MessageBus


def receptor_com_erro(message: Message) -> None:
    raise RuntimeError("Falha ao processar a mensagem")


def main() -> None:
    bus = MessageBus()

    receptor_erro = CallbackReceiverAdapter(receptor_com_erro)
    receptor_ok = CollectingReceiver()

    erro_id = bus.subscribe("producao", receptor_erro)
    ok_id = bus.subscribe("producao", receptor_ok)

    result = bus.publish("producao", "Lote concluído")

    # Aceitar o conteúdo não significa que todas as entregas tiveram sucesso.
    assert result.accepted and result.rejection_reason is None
    assert [delivery.succeeded for delivery in result.deliveries] == [False, True]
    falha, sucesso = result.deliveries
    assert falha.subscription_id == erro_id
    assert falha.error_type == "RuntimeError"
    assert falha.error_message == "Falha ao processar a mensagem"
    assert sucesso.subscription_id == ok_id and sucesso.error_message is None
    assert receptor_ok.messages == (result.message,)

    for delivery in result.deliveries:
        print("Entrega realizada:", delivery.succeeded)
        print("Erro:", delivery.error_message)

    print("Mensagens recebidas pelo segundo receptor:")
    print([message.content for message in receptor_ok.messages])


if __name__ == "__main__":
    main()
