"""Observer e Facade: uma publicação notifica dois receptores prontos."""

from canalbus import CollectingReceiver, MessageBus


def main() -> None:
    bus = MessageBus()

    production = CollectingReceiver()
    test2 = CollectingReceiver()
    audit = CollectingReceiver()

    subscription_id = bus.subscribe("producao", production)

    bus.subscribe("producao", audit)

    bus.subscribe("teste", test2)

    assert bus.subscribe(" producao ", production) == subscription_id

    result = bus.publish("producao", "A produção do ultimo lote foi concluida, por favor venham retirar.", {"lote": 42})

    assert result.accepted and len(result.deliveries) == 2
    assert all(delivery.succeeded for delivery in result.deliveries)
    assert production.messages == audit.messages == (result.message,)
    assert test2.messages == ()
    print(f"Broadcast: {len(result.deliveries)} entregas concluídas em produção.")
    print(f"Produção: {production.messages}")
    print(f"Auditoria: {audit.messages}")
    print(f"Teste: {test2.messages}")


if __name__ == "__main__":
    main()

