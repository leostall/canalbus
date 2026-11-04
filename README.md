# Canalbus

Biblioteca Python de mensagens por canais, síncrona e em memória. Uma aplicação
importa o pacote, inscreve receptores e publica mensagens. O código do pacote
não abre servidor, não imprime resultados e não depende de rede ou banco.

Projeto acadêmico de Design Patterns para quatro integrantes. Os oito padrões
implementados são **Facade, Builder, Observer, Strategy, Chain of Responsibility,
Decorator, Command e Adapter**. A biblioteca centraliza a distribuição de
mensagens entre componentes da aplicação, permitindo trocar regras de validação,
seleção e tratamento sem alterar o núcleo.

## Integrantes

- Leonardo Stall
- Giovanna Santos Daniel
- João Lucas do Prado Ribeiro
- Mirella Haisi Szvarça

## Vídeo de apresentação

**Pendente: adicionar aqui o link do vídeo no YouTube.**

<!-- Substituir a frase acima por: [Assistir à apresentação](URL_DO_VIDEO) -->

O vídeo pode ser não listado. Deve apresentar o objetivo da biblioteca, demonstrar
o uso padrão e uma extensão criada pelo consumidor. Cada integrante deve explicar
dois padrões diferentes, mostrando o código, o problema resolvido e a justificativa
da escolha; para os quatro integrantes, são oito padrões distintos ao todo.

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

Após instalar o pacote e ativar o ambiente virtual:

```bash
python -m pytest
python examples/01_basic_broadcast.py
python examples/02_round_robin.py
python examples/03_queued_delivery.py
python examples/04_callback_adapter.py
python examples/05_timing_decorator.py
python examples/06_external_extensions.py
python examples/07_delivery_failure.py
python examples/08_validation_chain.py
python -m build
```

| Exemplo | O que demonstra e verifica |
| --- | --- |
| [01 — Broadcast](examples/01_basic_broadcast.py) | Dois receptores notificados, isolamento entre canais e deduplicação de inscrições |
| [02 — Round Robin](examples/02_round_robin.py) | Alternância de destinatários com cursor independente por canal |
| [03 — Fila](examples/03_queued_delivery.py) | FIFO, processamento parcial e preservação dos destinatários após remover uma inscrição |
| [04 — Adapter](examples/04_callback_adapter.py) | Uso de uma função existente como receptor |
| [05 — Decorator](examples/05_timing_decorator.py) | Medições registradas tanto no sucesso quanto na falha |
| [06 — Extensões externas](examples/06_external_extensions.py) | Receptor, estratégia e validador definidos pelo consumidor, usando apenas a API pública |
| [07 — Falha de entrega](examples/07_delivery_failure.py) | Conteúdo aceito com uma entrega malsucedida, sem bloquear o receptor seguinte |
| [08 — Cadeia de validação](examples/08_validation_chain.py) | Rejeições por conteúdo vazio, tamanho e uma regra externa de liberação; entrega apenas após aprovação de toda a cadeia |

Todos os exemplos contêm asserções sobre os resultados. A suíte em
[tests/test_examples.py](tests/test_examples.py) descobre os arquivos `examples/*.py`
e executa cada um em um processo com diretório de trabalho externo ao projeto,
verificando que o pacote instalado pode ser importado pelo consumidor.

`python -m build` gera wheel e distribuição de fontes em `dist/`. Para importar
em outro projeto, instale o wheel no ambiente desse projeto:

```bash
python -m pip install /caminho/para/canalbus/dist/canalbus-0.1.0-py3-none-any.whl
```

## Arquitetura e padrões de projeto

O fluxo de uma publicação é: criar a mensagem, validar o conteúdo, obter as
inscrições do canal, selecionar destinatários, criar comandos e executá-los ou
enfileirá-los. Os resultados distinguem rejeição de conteúdo, agendamento e falha
de entrega. O núcleo fica em `src/canalbus`; `examples` contém código consumidor
e `tests` contém a validação automatizada.

| Padrão | Onde está implementado | Problema resolvido e justificativa |
| --- | --- | --- |
| **Facade** | [`MessageBus`](src/canalbus/bus.py): `subscribe`, `publish`, `process_pending` | Oferece uma entrada simples que coordena registro, validação, seleção e execução, sem exigir que o consumidor monte esses componentes manualmente. |
| **Builder** | [`MessageBusBuilder`](src/canalbus/builder.py): métodos `with_*`, `add_validator` e `build` | Monta configurações variadas com uma API fluente; fábricas criam componentes independentes a cada construção. |
| **Observer** | [`SubscriptionRegistry`](src/canalbus/subscriptions.py), [`Receiver`](src/canalbus/receivers.py) e `MessageBus.publish` | Mantém inscrições por canal e notifica receptores pelo contrato `receive`, desacoplando quem publica de quem trata a mensagem. No Broadcast, todos os inscritos são notificados. |
| **Strategy** | [`DispatchStrategy`, `BroadcastStrategy` e `RoundRobinStrategy`](src/canalbus/strategies.py) | Troca o algoritmo de seleção por composição; novas estratégias implementam `select` sem modificar o barramento. |
| **Chain of Responsibility** | [`MessageValidator`](src/canalbus/validation.py): `set_next`, `validate` e `check` | Encadeia regras independentes e interrompe na primeira rejeição; o Builder permite acrescentar validadores externos. |
| **Decorator** | [`TimingReceiverDecorator`](src/canalbus/receivers.py) | Envolve qualquer `Receiver` para medir duração e sucesso sem alterar sua implementação, mantendo o mesmo contrato. |
| **Command** | [`DeliverMessageCommand`](src/canalbus/commands.py) e [executores](src/canalbus/execution.py) | Encapsula uma tentativa com mensagem e destinatário, permitindo execução imediata ou posterior em FIFO sem mudar o receptor. |
| **Adapter** | [`CallbackReceiverAdapter`](src/canalbus/receivers.py) | Converte a chamada `receive(message)` em uma chamada à função fornecida, permitindo integrar callbacks à interface de receptores. |

Adapter e Decorator têm funções distintas: o primeiro adapta uma função ao contrato
`Receiver`; o segundo já recebe um `Receiver` e adiciona medições. Observer mantém
os interessados na mensagem, enquanto Strategy decide quais deles recebem cada
publicação. Essas diferenças devem aparecer na defesa dos padrões.

A separação entre modelos, inscrições, validação, seleção e execução mantém as
responsabilidades pequenas. Os contratos abstratos e a injeção de componentes
permitem extensões pelo consumidor (Open/Closed Principle). Mensagens imutáveis,
resultados explícitos e testes de falhas ajudam a tornar o comportamento previsível.

## Conferência dos requisitos da atividade

| Requisito das imagens | Situação no projeto |
| --- | --- |
| Biblioteca importável para outros desenvolvedores | Atendido: pacote Python configurado em `pyproject.toml`, sem servidor ou aplicação final no núcleo |
| Funcionalidade pronta para uso | Atendido: `MessageBus()` oferece Broadcast, execução imediata e validadores padrão; há um receptor concreto pronto |
| Extensibilidade sem alterar a biblioteca | Atendido: contratos públicos `Receiver`, `DispatchStrategy` e `MessageValidator`, demonstrados nos exemplos 06 e 08 |
| Design Patterns e Clean Code | Oito padrões identificados acima, com responsabilidades separadas e testes; a justificativa oral ainda deve ser apresentada pelo grupo |
| Equipe com até quatro alunos e nomes no README | Quatro integrantes listados acima; conferir se os nomes estão completos antes da entrega |
| Código hospedado em repositório | Repositório público: [leostall/canalbus](https://github.com/leostall/canalbus); enviar as alterações locais antes de entregar |
| Documentação de uso no README | Instalação, primeiro uso, API, fila, extensões, exemplos e limitações documentados aqui |
| Link do vídeo no YouTube | **Pendente**, na seção reservada acima |
| Conteúdo obrigatório do vídeo | **Pendente de gravação/verificação**: visão geral, uso padrão, extensão e defesa dos oito padrões, dois por integrante |
| Entrega de apenas um link para o repositório | A realizar pelo grupo até **18/11**, conforme o enunciado |

Os temas da terceira imagem são sugestões; o enunciado permite tema livre.
Uma biblioteca de mensagens por canais se enquadra nesse escopo. A existência
dos padrões e dos exemplos não substitui a explicação individual exigida no vídeo.

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

