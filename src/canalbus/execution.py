"""Executores internos; a fila conhece comandos, não detalhes de receptores."""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from enum import Enum

from .commands import DeliverMessageCommand
from .models import DeliveryResult, ProcessingResult


class ExecutionMode(Enum):
    """Modos disponíveis, ambos síncronos e sem processamento em background."""

    IMMEDIATE = "immediate"
    QUEUED = "queued"


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    deliveries: tuple[DeliveryResult, ...] = ()
    queued_count: int = 0


class DeliveryExecutor(ABC):
    @abstractmethod
    def submit(self, commands: tuple[DeliverMessageCommand, ...]) -> ExecutionResult:
        """Executa ou agenda o lote de comandos."""

    @abstractmethod
    def process_pending(self, limit: int | None) -> ProcessingResult:
        """Executa até limit comandos da fotografia inicial da fila."""

    @property
    @abstractmethod
    def pending_count(self) -> int:
        """Número de comandos aguardando execução."""


class ImmediateExecutor(DeliveryExecutor):
    def submit(self, commands: tuple[DeliverMessageCommand, ...]) -> ExecutionResult:
        return ExecutionResult(tuple(command.execute() for command in commands))

    def process_pending(self, limit: int | None) -> ProcessingResult:
        return ProcessingResult((), 0)

    @property
    def pending_count(self) -> int:
        return 0


class QueuedExecutor(DeliveryExecutor):
    def __init__(self) -> None:
        self._commands: deque[DeliverMessageCommand] = deque()
        self._processing = False

    def submit(self, commands: tuple[DeliverMessageCommand, ...]) -> ExecutionResult:
        self._commands.extend(commands)
        return ExecutionResult(queued_count=len(commands))

    def process_pending(self, limit: int | None) -> ProcessingResult:
        if self._processing:
            raise RuntimeError("process_pending não pode ser chamado recursivamente.")
        initial_count = len(self._commands)
        budget = initial_count if limit is None else min(limit, initial_count)
        self._processing = True
        try:
            results = []
            for _ in range(budget):
                command = self._commands.popleft()
                results.append(command.execute())
            return ProcessingResult(tuple(results), len(self._commands))
        finally:
            self._processing = False

    @property
    def pending_count(self) -> int:
        return len(self._commands)
