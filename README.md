# canalbus

Biblioteca Python de mensagens por canais, síncrona e em memória. Uma aplicação
importa o pacote, inscreve receptores e publica mensagens. O código do pacote
não abre servidor, não imprime resultados e não depende de rede ou banco.

Projeto acadêmico de Design Patterns para quatro integrantes. Os oito padrões
implementados são **Facade, Builder, Observer, Strategy, Chain of Responsibility,
Decorator, Command e Adapter**. Veja [a explicação dos padrões](docs/padroes.md).

## Instalação

Requer Python **3.11 ou superior**. Na pasta que contém `pyproject.toml`:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell, em vez do comando anterior:
# .venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
```

O pacote de produção usa apenas a biblioteca padrão. O extra `dev` instala
pytest e build. Para somente consumir a biblioteca, use `python -m pip install .`.
Não é necessário publicar no PyPI.

## Primeiro uso

```python
from canalbus import CollectingReceiver, MessageBus

bus = MessageBus()
receiver = CollectingReceiver()
subscription_id = bus.subscribe("producao", receiver)

result = bus.publish("producao", "Lote concluído", {"lote": 42})
assert result.accepted
assert result.deliveries[0].succeeded
assert receiver.messages[0].content == "Lote concluído"
assert bus.unsubscribe(subscription_id)
```

Por padrão: Broadcast, execução imediata, conteúdo não vazio e limite de
**1.000 caracteres**. O comprimento usa `len(content)`, incluindo espaços.
O canal tem espaços das extremidades removidos e diferencia maiúsculas de
minúsculas: `" producao "` equivale a `"producao"`; `"Producao"` é outro canal.

## Operações principais

| API | Retorno e comportamento |
| --- | --- |
| `MessageBus()` | Barramento funcional com a configuração padrão |
| `subscribe(channel, receiver)` | ID em string; mesma instância no mesmo canal devolve o ID existente |
| `unsubscribe(subscription_id)` | `True` se removeu; `False` se não existia |
| `publish(channel, content, metadata=None)` | `PublishResult`: aceitação, motivo, entregas executadas ou quantidade enfileirada |
| `pending_count` | Quantidade de comandos pendentes, não de mensagens |
| `process_pending(limit=None)` | `ProcessingResult` com entregas tentadas e quantidade restante |
| `receiver.messages` | Tupla com uma fotografia das mensagens coletadas |
| `decorator.measurements` | Tupla com durações em segundos e indicação de sucesso |

`PublishResult.accepted` significa que o **conteúdo foi aprovado**. Não significa
que todos os receptores o trataram com sucesso. Uma publicação válida sem
inscritos é aceita com zero entregas. No modo enfileirado, `deliveries` é vazio
e `queued_count` indica agendamento, nunca sucesso de entrega.

Cada `DeliveryResult` tem `message_id`, `subscription_id`, `succeeded`,
`error_type` e `error_message`. Uma falha de receptor não impede os demais.
Argumentos incorretos geram `TypeError` ou `ValueError`; rejeições de conteúdo
aparecem em `rejection_reason`. Exceções de extensões na validação ou seleção
propagam como erros de programação, antes de criar comandos.

## Builder e fila

```python
from canalbus import (
    CollectingReceiver, ExecutionMode, MessageBusBuilder, RoundRobinStrategy,
)

builder = (
    MessageBusBuilder()
    .with_strategy(RoundRobinStrategy)
    .with_execution_mode(ExecutionMode.QUEUED)
    .with_max_length(250)
)
bus = builder.build()
receiver = CollectingReceiver()
bus.subscribe("manutencao", receiver)

published = bus.publish("manutencao", "Verificar sensor")
assert published.queued_count == 1
assert published.deliveries == ()
processed = bus.process_pending(limit=10)
assert processed.processed_count == 1
assert processed.deliveries[0].succeeded
```

O Builder é reutilizável e mantém sua configuração. `build()` cria novas filas,
inscrições, estratégias e cadeias. `with_strategy` e `add_validator` recebem
**fábricas sem argumentos**, como a classe `RoundRobinStrategy` ou
`lambda: MeuValidador("origem")`. Cada fábrica deve criar uma instância nova;
retornar uma instância compartilhada viola esse contrato. Objetos externos
capturados por uma fábrica não são clonados. Alterar o Builder não reconfigura
barramentos já criados.

Os validadores padrão vêm primeiro: conteúdo não vazio, tamanho máximo e,
depois, os adicionais na ordem de `add_validator`. Uma rejeição interrompe a
cadeia. O Builder recebe elos avulsos e monta suas ligações.

As entregas pendentes mantêm os destinatários da publicação. Remover uma
inscrição não cancela comandos existentes; novos inscritos não recebem
mensagens antigas. A fila é FIFO, inclusive dentro de cada publicação, seguindo
a ordem selecionada pela estratégia. Cada chamada processa no máximo os comandos
que existiam no início, mesmo com limite maior. `limit` deve ser inteiro positivo;
`None` processa toda essa fotografia inicial. `bool` não é aceito como inteiro.
Chamadas recursivas de `process_pending` são rejeitadas com `RuntimeError`.

O Round Robin usa um cursor por canal. Antes da seleção, aplica o resto da
divisão do cursor pelo tamanho da lista atual. Mudanças de participantes podem
fazer alguém receber novamente ou esperar uma publicação a mais. A ordem é
posicional; não há promessa de justiça durante alterações de inscrições.
Uma publicação válida sem inscritos zera o cursor daquele canal.

## Extensão pelo consumidor

Implemente `Receiver.receive`, `MessageValidator.check` ou
`DispatchStrategy.select`, importando somente de `canalbus`.
Validadores que definirem `__init__` devem chamar `super().__init__()`.
`check` devolve `None` para aprovar ou uma string não vazia para rejeitar.
`select` devolve uma tupla sem repetições, com objetos da fotografia recebida.
Veja [o exemplo completo externo](examples/06_external_extensions.py).

`CallbackReceiverAdapter(funcao)` permite usar uma função `funcao(message)`.
`TimingReceiverDecorator(receiver)` acrescenta medições ao receptor sem alterar
sua classe; registra sucesso e falha com `perf_counter`, sem imprimir nada.

## Testes, exemplos e empacotamento

```bash
python -m pytest
python examples/01_basic_broadcast.py
python examples/02_round_robin.py
python examples/03_queued_delivery.py
python examples/04_callback_adapter.py
python examples/05_timing_decorator.py
python examples/06_external_extensions.py
python -m build
```

`python -m build` gera wheel e distribuição de fontes em `dist/`. Para importar
em outro projeto: `python -m pip install /caminho/canalbus-0.1.0-py3-none-any.whl`.
Veja os comandos realmente executados em [validação](docs/validacao.md).

## Documentação para o grupo

- [Arquitetura e decisões](docs/arquitetura.md)
- [Os oito padrões, com trechos do código](docs/padroes.md)
- [Roteiro de apresentação para quatro integrantes](docs/roteiro.md)
- [Requisitos e testes correspondentes](docs/requisitos.md)
- [Validações executadas](docs/validacao.md)

## Limitações

- Síncrona, no mesmo processo e sem garantia de segurança para uso concorrente.
- Sem threads, asyncio, servidor, interface, persistência ou comunicação remota.
- Mensagens, inscrições, fila e históricos desaparecem ao terminar o processo.
- Sem reenvio automático, confirmação de leitura ou garantia de entrega exatamente uma vez.
- Sem limite de capacidade para fila e históricos; a aplicação deve controlar seu uso de memória.
- Captura `Exception` em cada entrega. `KeyboardInterrupt`, `SystemExit` e outras
  `BaseException` propagam e interrompem a chamada. Na fila, o comando já
  retirado não é reinserido; os ainda pendentes permanecem.
- Publicar recursivamente no modo imediato é síncrono e pode esgotar a pilha;
  para encadear mensagens, prefira o modo enfileirado com processamento manual.
- Metadados aceitam apenas chaves string e valores `str`, `int`, `float`, `bool`
  ou `None`; não aceitam listas, dicionários aninhados ou objetos arbitrários.
- Não substitui um broker distribuído. Não promete cancelamento, prioridades,
  ordenação entre processos nem desfazer entregas.

