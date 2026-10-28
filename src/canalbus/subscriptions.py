"""Registro de observadores com deduplicação por identidade do receptor."""

from dataclasses import dataclass, field
from uuid import uuid4

from .models import normalize_channel
from .receivers import Receiver


@dataclass(frozen=True, slots=True)
class Subscription:
    """Associação pública entre canal, receptor e identificador de inscrição."""

    channel: str
    receiver: Receiver
    id: str = field(default_factory=lambda: str(uuid4()), init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "channel", normalize_channel(self.channel))
        if not isinstance(self.receiver, Receiver):
            raise TypeError("receiver deve implementar Receiver.")


class SubscriptionRegistry:
    """Mantém inscrições em ordem de inserção, isoladas por barramento."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, Subscription] = {}

    def subscribe(self, channel: str, receiver: Receiver) -> str:
        channel = normalize_channel(channel)
        if not isinstance(receiver, Receiver):
            raise TypeError("receiver deve implementar Receiver.")
        for subscription in self._subscriptions.values():
            if subscription.channel == channel and subscription.receiver is receiver:
                return subscription.id
        subscription = Subscription(channel, receiver)
        self._subscriptions[subscription.id] = subscription
        return subscription.id

    def unsubscribe(self, subscription_id: str) -> bool:
        if not isinstance(subscription_id, str):
            raise TypeError("subscription_id deve ser uma string.")
        return self._subscriptions.pop(subscription_id, None) is not None

    def snapshot(self, channel: str) -> tuple[Subscription, ...]:
        return tuple(
            subscription
            for subscription in self._subscriptions.values()
            if subscription.channel == channel
        )

