from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

from canalbus import CallbackReceiverAdapter, CollectingReceiver, Message, MessageBus


def test_message_identity_timestamp_and_preserved_content():
    first = Message(" producao ", "  texto  ")
    second = Message("producao", "  texto  ")
    assert first.channel == "producao"
    assert first.content == "  texto  "
    assert UUID(first.id).version == 4
    assert first.id != second.id
    assert first.created_at.tzinfo is not None
    assert first.created_at.utcoffset().total_seconds() == 0


def test_message_and_metadata_are_immutable_copies():
    source = {"origem": "linha-1", "count": 2, "ratio": 1.5, "ok": True, "extra": None}
    message = Message("a", "b", source)
    source["origem"] = "alterada"
    assert message.metadata["origem"] == "linha-1"
    with pytest.raises(FrozenInstanceError):
        message.content = "alterado"
    with pytest.raises(TypeError):
        message.metadata["origem"] = "alterada"


@pytest.mark.parametrize("metadata", [[], "texto", 42, {1: "x"}, {"x": []}, {"x": {}}, {"x": object()}])
def test_invalid_metadata_is_structural_error(metadata):
    with pytest.raises(TypeError):
        MessageBus().publish("canal", "conteudo", metadata)


@pytest.mark.parametrize("channel", [None, 12, [], True])
def test_channel_wrong_type(channel):
    with pytest.raises(TypeError):
        MessageBus().publish(channel, "texto")


@pytest.mark.parametrize("channel", ["", "  ", "\n\t"])
def test_channel_blank(channel):
    with pytest.raises(ValueError):
        MessageBus().publish(channel, "texto")


@pytest.mark.parametrize("content", [None, 12, [], True])
def test_content_wrong_type(content):
    with pytest.raises(TypeError):
        MessageBus().publish("canal", content)


def test_mutating_receiver_cannot_corrupt_next_delivery():
    bus = MessageBus()
    collector = CollectingReceiver()

    def mutate(message):
        message.metadata["origem"] = "corrompida"

    bus.subscribe("a", CallbackReceiverAdapter(mutate))
    bus.subscribe("a", collector)
    result = bus.publish("a", "texto", {"origem": "original"})
    assert [delivery.succeeded for delivery in result.deliveries] == [False, True]
    assert collector.messages[0].metadata["origem"] == "original"


def test_collector_returns_snapshot():
    collector = CollectingReceiver()
    old_snapshot = collector.messages
    message = Message("a", "b")
    collector.receive(message)
    assert old_snapshot == ()
    assert collector.messages == (message,)

