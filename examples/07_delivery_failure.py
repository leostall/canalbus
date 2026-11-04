from canalbus import CallbackReceiverAdapter, CollectingReceiver, MessageBus


def receptor_com_erro(message):
    raise RuntimeError("Falha ao processar a mensagem")


def main():
    bus = MessageBus()

    receptor_erro = CallbackReceiverAdapter(receptor_com_erro)
    receptor_ok = CollectingReceiver()

    bus.subscribe("producao", receptor_erro)
    bus.subscribe("producao", receptor_ok)

    result = bus.publish("producao", "Lote concluído")

    for delivery in result.deliveries:
        print("Entrega realizada:", delivery.succeeded)
        print("Erro:", delivery.error_message)

    print("Mensagens recebidas pelo segundo receptor:")
    print([message.content for message in receptor_ok.messages])


if __name__ == "__main__":
    main()
