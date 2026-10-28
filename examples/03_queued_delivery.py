"""Command: destinatários capturados e processamento manual em FIFO."""

from canalbus import CollectingReceiver, ExecutionMode, MessageBusBuilder


def main() -> None:
    bus = MessageBusBuilder().with_execution_mode(ExecutionMode.QUEUED).build()
    original, newcomer = CollectingReceiver(), CollectingReceiver()
    subscription_id = bus.subscribe("producao", original)
    first = bus.publish("producao", "Lote 1")
    bus.publish("producao", "Lote 2")
    assert first.queued_count == 1 and first.deliveries == ()
    assert original.messages == ()
    bus.unsubscribe(subscription_id)
    bus.subscribe("producao", newcomer)
    result = bus.process_pending(limit=1)
    assert result.processed_count == 1 and result.remaining_count == 1
    print("Após a primeira chamada:", original.messages[0].content)
    bus.process_pending()
    assert [message.content for message in original.messages] == ["Lote 1", "Lote 2"]
    assert newcomer.messages == () and bus.pending_count == 0
    print("Inscrição removida recebeu os dois comandos antigos; novo receptor recebeu zero.")


if __name__ == "__main__":
    main()

