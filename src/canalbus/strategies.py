"""Políticas substituíveis de seleção de destinatários."""

from abc import ABC, abstractmethod

from .models import Message
from .subscriptions import Subscription


class DispatchStrategy(ABC):
    """Uma fábrica de estratégia deve fornecer uma instância nova por bus."""

    @abstractmethod
    def select(
        self, message: Message, subscriptions: tuple[Subscription, ...]
    ) -> tuple[Subscription, ...]:
        """Seleciona um subconjunto sem repetições da fotografia recebida."""


class BroadcastStrategy(DispatchStrategy):
    """Seleciona todos os observadores na ordem de inscrição."""

    def select(
        self, message: Message, subscriptions: tuple[Subscription, ...]
    ) -> tuple[Subscription, ...]:
        """Devolve a fotografia inteira, sem modificar as inscrições."""
        return subscriptions


class RoundRobinStrategy(DispatchStrategy):
    """Seleciona uma posição por publicação, com cursor independente por canal."""

    def __init__(self) -> None:
        self._next_indices: dict[str, int] = {}

    def select(
        self, message: Message, subscriptions: tuple[Subscription, ...]
    ) -> tuple[Subscription, ...]:
        """Ajusta o cursor pelo módulo do tamanho da fotografia atual."""
        if not subscriptions:
            self._next_indices.pop(message.channel, None)
            return ()
        index = self._next_indices.get(message.channel, 0) % len(subscriptions)
        self._next_indices[message.channel] = index + 1
        return (subscriptions[index],)

