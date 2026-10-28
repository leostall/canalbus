"""Mensagens e resultados públicos, independentes dos mecanismos de entrega."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import TypeAlias
from uuid import uuid4

MetadataValue: TypeAlias = str | int | float | bool | None


def normalize_channel(channel: str) -> str:
    """Valida e remove espaços das extremidades; preserva a capitalização."""
    if not isinstance(channel, str):
        raise TypeError("channel deve ser uma string.")
    normalized = channel.strip()
    if not normalized:
        raise ValueError("channel não pode ser vazio.")
    return normalized


def require_positive_integer(value: int, name: str) -> None:
    """Rejeita inclusive bool, que em Python é uma subclasse de int."""
    if type(value) is not int:
        raise TypeError(f"{name} deve ser um inteiro positivo.")
    if value <= 0:
        raise ValueError(f"{name} deve ser maior que zero.")


@dataclass(frozen=True, slots=True)
class Message:
    """Mensagem imutável; metadados são copiados e protegidos contra escrita."""

    channel: str
    content: str
    metadata: Mapping[str, MetadataValue] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()), init=False)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), init=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "channel", normalize_channel(self.channel))
        if not isinstance(self.content, str):
            raise TypeError("content deve ser uma string.")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata deve ser um mapeamento.")
        copied = dict(self.metadata)
        for key, value in copied.items():
            if not isinstance(key, str):
                raise TypeError("As chaves de metadata devem ser strings.")
            # Tipos exatos impedem objetos mutáveis disfarçados de escalares.
            if type(value) not in (str, int, float, bool, type(None)):
                raise TypeError("metadata aceita apenas str, int, float, bool e None.")
        object.__setattr__(self, "metadata", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Resultado de uma tentativa, sem reter a exceção e seu traceback."""

    message_id: str
    subscription_id: str
    succeeded: bool
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class PublishResult:
    """Aceitação do conteúdo é distinta do sucesso das entregas."""

    message: Message
    accepted: bool
    rejection_reason: str | None = None
    deliveries: tuple[DeliveryResult, ...] = ()
    queued_count: int = 0

    @property
    def selected_count(self) -> int:
        """Número de destinatários selecionados nesta publicação."""
        return len(self.deliveries) + self.queued_count


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    """Tentativas realizadas e tamanho da fila ao terminar o processamento."""

    deliveries: tuple[DeliveryResult, ...]
    remaining_count: int

    @property
    def processed_count(self) -> int:
        """Quantidade de comandos executados, incluindo falhas."""
        return len(self.deliveries)


@dataclass(frozen=True, slots=True)
class TimingMeasurement:
    """Duração em segundos de uma chamada ao receptor decorado."""

    message_id: str
    duration_seconds: float
    succeeded: bool

