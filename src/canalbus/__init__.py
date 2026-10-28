"""API pública de canalbus: mensagens síncronas por canais, em memória."""

from .builder import MessageBusBuilder
from .bus import MessageBus
from .commands import DeliverMessageCommand
from .execution import ExecutionMode
from .models import (
    DeliveryResult,
    Message,
    MetadataValue,
    ProcessingResult,
    PublishResult,
    TimingMeasurement,
)
from .receivers import (
    CallbackReceiverAdapter,
    CollectingReceiver,
    Receiver,
    TimingReceiverDecorator,
)
from .strategies import BroadcastStrategy, DispatchStrategy, RoundRobinStrategy
from .subscriptions import Subscription
from .validation import MaxLengthValidator, MessageValidator, NonEmptyContentValidator

__all__ = [
    "BroadcastStrategy",
    "CallbackReceiverAdapter",
    "CollectingReceiver",
    "DeliverMessageCommand",
    "DeliveryResult",
    "DispatchStrategy",
    "ExecutionMode",
    "MaxLengthValidator",
    "Message",
    "MessageBus",
    "MessageBusBuilder",
    "MessageValidator",
    "MetadataValue",
    "NonEmptyContentValidator",
    "ProcessingResult",
    "PublishResult",
    "Receiver",
    "RoundRobinStrategy",
    "Subscription",
    "TimingMeasurement",
    "TimingReceiverDecorator",
]
