"""Builder reutilizável: monta componentes novos e encadeia validadores."""

from collections.abc import Callable

from .bus import MessageBus
from .execution import ExecutionMode
from .models import require_positive_integer
from .strategies import BroadcastStrategy, DispatchStrategy
from .validation import MaxLengthValidator, MessageValidator, NonEmptyContentValidator


class MessageBusBuilder:
    """Guarda configuração e fábricas, sem guardar filas ou inscrições.

    Cada fábrica deve devolver uma instância nova, sem argumentos. Para uma
    extensão com estado, use sua classe ou lambda: MinhaClasse(configuracao).
    Retornar um singleton viola esse contrato: não há cópia mágica de objetos
    ou de recursos externos capturados pelas fábricas.
    """

    def __init__(self) -> None:
        self._strategy_factory: Callable[[], DispatchStrategy] = BroadcastStrategy
        self._mode = ExecutionMode.IMMEDIATE
        self._max_length = 1000
        self._validator_factories: list[Callable[[], MessageValidator]] = []

    def with_strategy(
        self, factory: Callable[[], DispatchStrategy]
    ) -> "MessageBusBuilder":
        """Configura a fábrica; passe RoundRobinStrategy, sem parênteses."""
        if not callable(factory):
            raise TypeError("factory deve criar uma DispatchStrategy e ser chamável.")
        self._strategy_factory = factory
        return self

    def with_execution_mode(self, mode: ExecutionMode) -> "MessageBusBuilder":
        """Seleciona execução imediata ou fila manual."""
        if not isinstance(mode, ExecutionMode):
            raise TypeError("mode deve ser um ExecutionMode.")
        self._mode = mode
        return self

    def with_max_length(self, max_length: int) -> "MessageBusBuilder":
        """Configura um limite positivo, contado com len(content)."""
        require_positive_integer(max_length, "max_length")
        self._max_length = max_length
        return self

    def add_validator(
        self, factory: Callable[[], MessageValidator]
    ) -> "MessageBusBuilder":
        """Acrescenta uma fábrica de elo avulso, depois dos validadores padrão."""
        if not callable(factory):
            raise TypeError("factory deve criar um MessageValidator e ser chamável.")
        self._validator_factories.append(factory)
        return self

    def build(self) -> MessageBus:
        """Cria componentes, valida os contratos e monta a cadeia na ordem definida."""
        strategy = self._strategy_factory()
        if not isinstance(strategy, DispatchStrategy):
            raise TypeError("A fábrica de estratégia deve retornar DispatchStrategy.")
        additional = [factory() for factory in self._validator_factories]
        for validator in additional:
            if not isinstance(validator, MessageValidator):
                raise TypeError("A fábrica de validador deve retornar MessageValidator.")
            if validator._next is not None:
                raise ValueError("Cada fábrica deve retornar um validador sem próximo elo.")
        if len({id(validator) for validator in additional}) != len(additional):
            raise ValueError("Cada fábrica deve retornar uma instância distinta de validador.")
        head = NonEmptyContentValidator()
        tail = head.set_next(MaxLengthValidator(self._max_length))
        for validator in additional:
            tail = tail.set_next(validator)
        return MessageBus(strategy=strategy, validator=head, mode=self._mode)

