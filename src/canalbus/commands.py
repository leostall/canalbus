"""Command compartilhado pelas execuções imediata e enfileirada."""

from dataclasses import dataclass

from .models import DeliveryResult, Message
from .subscriptions import Subscription


@dataclass(frozen=True, slots=True)
class DeliverMessageCommand:
    """Captura mensagem e inscrição no momento da publicação."""

    message: Message
    subscription: Subscription

    def execute(self) -> DeliveryResult:
        """Faz uma tentativa; registra Exception e deixa BaseException propagar."""
        try:
            self.subscription.receiver.receive(self.message)
        except Exception as error:
            return DeliveryResult(
                self.message.id,
                self.subscription.id,
                False,
                type(error).__name__,
                str(error),
            )
        return DeliveryResult(self.message.id, self.subscription.id, True)

