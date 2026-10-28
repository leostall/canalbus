"""Contrato de Observer, receptor concreto, Adapter e Decorator."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from time import perf_counter

from .models import Message, TimingMeasurement


class Receiver(ABC):
    """Contrato síncrono implementado pelos destinatários das mensagens."""

    @abstractmethod
    def receive(self, message: Message) -> None:
        """Trata a mensagem ou levanta uma exceção se o tratamento falhar."""


class CollectingReceiver(Receiver):
    """Armazena mensagens em memória para consulta e demonstração."""

    def __init__(self) -> None:
        self._messages: list[Message] = []

    def receive(self, message: Message) -> None:
        """Acrescenta a mensagem ao histórico."""
        self._messages.append(message)

    @property
    def messages(self) -> tuple[Message, ...]:
        """Retorna uma fotografia imutável do histórico."""
        return tuple(self._messages)


class CallbackReceiverAdapter(Receiver):
    """Adapta callback(message) para a interface receive(message)."""

    def __init__(self, callback: Callable[[Message], None]) -> None:
        if not callable(callback):
            raise TypeError("callback deve ser chamável.")
        self._callback = callback

    def receive(self, message: Message) -> None:
        """Encaminha a mensagem; falhas seguem para o comando de entrega."""
        self._callback(message)


class TimingReceiverDecorator(Receiver):
    """Adiciona medições a qualquer Receiver, preservando suas exceções."""

    def __init__(self, receiver: Receiver) -> None:
        if not isinstance(receiver, Receiver):
            raise TypeError("receiver deve implementar Receiver.")
        self._receiver = receiver
        self._measurements: list[TimingMeasurement] = []

    def receive(self, message: Message) -> None:
        """Mede também falhas, sem capturar ou substituir a exceção original."""
        started_at = perf_counter()
        succeeded = False
        try:
            self._receiver.receive(message)
            succeeded = True
        finally:
            self._measurements.append(
                TimingMeasurement(message.id, perf_counter() - started_at, succeeded)
            )

    @property
    def measurements(self) -> tuple[TimingMeasurement, ...]:
        """Retorna uma fotografia imutável das medições."""
        return tuple(self._measurements)

