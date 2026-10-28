"""Observer e Facade: uma publicação notifica dois receptores prontos."""

from canalbus import CollectingReceiver, MessageBus


def main() -> None:
    bus = MessageBus()
    production = CollectingReceiver()
    audit = CollectingReceiver()

    subscription_id = bus.subscribe("producao", production)

    bus.subscribe("producao", audit)

    assert bus.subscribe(" producao ", production) == subscription_id

    result = bus.publish("producao", "Lote concluído", {"lote": 42})

    assert result.accepted and len(result.deliveries) == 2
    assert all(delivery.succeeded for delivery in result.deliveries)
    assert production.messages == audit.messages == (result.message,)
    
    print(f"Broadcast: {len(result.deliveries)} entregas concluídas.")


if __name__ == "__main__":
    main()

