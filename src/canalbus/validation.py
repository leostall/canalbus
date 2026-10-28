"""Chain of Responsibility explícita: cada elo conhece o próximo."""

from abc import ABC, abstractmethod

from .models import Message, require_positive_integer


class MessageValidator(ABC):
    """Implemente check; validate encaminha ao próximo elo após aprovação."""

    def __init__(self) -> None:
        self._next: MessageValidator | None = None

    def set_next(self, validator: "MessageValidator") -> "MessageValidator":
        """Liga o próximo elo e o devolve; rejeita ciclos na cadeia."""
        if not isinstance(validator, MessageValidator):
            raise TypeError("validator deve implementar MessageValidator.")
        current: MessageValidator | None = validator
        while current is not None:
            if current is self:
                raise ValueError("A cadeia de validação não pode conter ciclos.")
            current = current._next
        self._next = validator
        return validator

    def validate(self, message: Message) -> str | None:
        """Retorna a primeira rejeição, ou None quando toda a cadeia aprova."""
        reason = self.check(message)
        if reason is not None:
            if not isinstance(reason, str) or not reason.strip():
                raise TypeError("check deve retornar None ou um motivo não vazio.")
            return reason
        if self._next is not None:
            return self._next.validate(message)
        return None

    @abstractmethod
    def check(self, message: Message) -> str | None:
        """Avalia apenas este elo, preservando o conteúdo original."""


class NonEmptyContentValidator(MessageValidator):
    """Rejeita conteúdo vazio ou composto apenas de espaços em branco."""

    def check(self, message: Message) -> str | None:
        """Consulta strip sem alterar a mensagem."""
        if not message.content.strip():
            return "O conteúdo não pode ser vazio ou conter apenas espaços."
        return None


class MaxLengthValidator(MessageValidator):
    """Limita len(content), incluindo os espaços originais."""

    def __init__(self, max_length: int = 1000) -> None:
        super().__init__()
        require_positive_integer(max_length, "max_length")
        self._max_length = max_length

    def check(self, message: Message) -> str | None:
        """Aceita conteúdo com comprimento exatamente igual ao limite."""
        if len(message.content) > self._max_length:
            return f"O conteúdo excede o limite de {self._max_length} caracteres."
        return None

