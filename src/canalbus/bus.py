"""Facade que coordena publicação sem implementar cada comportamento."""

from collections.abc import Mapping

from .commands import DeliverMessageCommand
from .execution import ExecutionMode, ImmediateExecutor, QueuedExecutor
from .models import (
    Message,
    MetadataValue,
    ProcessingResult,
    PublishResult,
    require_positive_integer,
)
from .receivers import Receiver
from .strategies import BroadcastStrategy, DispatchStrategy
from .subscriptions import Subscription, SubscriptionRegistry
from .validation import MaxLengthValidator, MessageValidator, NonEmptyContentValidator


class MessageBus:
    """Barramento síncrono; sem argumentos, usa Broadcast e entrega imediata.

    strategy e validator são pontos de composição avançada e passam a pertencer
    a este barramento. Não reutilize suas instâncias em outro bus. Prefira o
    Builder com fábricas para criar vários barramentos independentes.
    """

    def __init__(
        self,
        *,
        strategy: DispatchStrategy | None = None,
        validator: MessageValidator | None = None,
        mode: ExecutionMode = ExecutionMode.IMMEDIATE,
    ) -> None:
        if strategy is not None and not isinstance(strategy, DispatchStrategy):
            raise TypeError("strategy deve implementar DispatchStrategy.")
        if validator is not None and not isinstance(validator, MessageValidator):
            raise TypeError("validator deve implementar MessageValidator.")
        if not isinstance(mode, ExecutionMode):
            raise TypeError("mode deve ser um ExecutionMode.")
        self._strategy = strategy if strategy is not None else BroadcastStrategy()
        if validator is None:
            validator = NonEmptyContentValidator()
            validator.set_next(MaxLengthValidator())
        self._validator = validator
        self._registry = SubscriptionRegistry()
        self._executor = (
            ImmediateExecutor() if mode is ExecutionMode.IMMEDIATE else QueuedExecutor()
        )

    def subscribe(self, channel: str, receiver: Receiver) -> str:
        """Inscreve por identidade; repetir a mesma associação devolve o mesmo ID."""
        return self._registry.subscribe(channel, receiver)

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove uma inscrição; não cancela entregas já enfileiradas."""
        return self._registry.unsubscribe(subscription_id)

    def publish(
        self,
        channel: str,
        content: str,
        metadata: Mapping[str, MetadataValue] | None = None,
    ) -> PublishResult:
        """Valida, seleciona uma fotografia de destinatários e agenda as entregas."""
        message = Message(channel, content, {} if metadata is None else metadata)
        reason = self._validator.validate(message)
        if reason is not None:
            return PublishResult(message, False, rejection_reason=reason)
        subscriptions = self._registry.snapshot(message.channel)
        selected = self._select(message, subscriptions)
        commands = tuple(DeliverMessageCommand(message, item) for item in selected)
        execution = self._executor.submit(commands)
        return PublishResult(
            message,
            True,
            deliveries=execution.deliveries,
            queued_count=execution.queued_count,
        )

    def _select(
        self, message: Message, subscriptions: tuple[Subscription, ...]
    ) -> tuple[Subscription, ...]:
        selected = self._strategy.select(message, subscriptions)
        if not isinstance(selected, tuple):
            raise TypeError("select deve retornar uma tupla de inscrições.")
        available = {id(item) for item in subscriptions}
        seen: set[int] = set()
        for item in selected:
            identity = id(item)
            if identity not in available:
                raise ValueError("A estratégia selecionou uma inscrição fora da fotografia.")
            if identity in seen:
                raise ValueError("A estratégia selecionou uma inscrição repetida.")
            seen.add(identity)
        return selected

    def process_pending(self, limit: int | None = None) -> ProcessingResult:
        """Processa até limit comandos iniciais; no modo imediato devolve zero."""
        if limit is not None:
            require_positive_integer(limit, "limit")
        return self._executor.process_pending(limit)

    @property
    def pending_count(self) -> int:
        """Quantidade atual de comandos pendentes, nunca de mensagens distintas."""
        return self._executor.pending_count

