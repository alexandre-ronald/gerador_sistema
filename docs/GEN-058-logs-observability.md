# GEN-058 — Logs & Observability

## Status

Draft 0.1 — arquitetura e contratos iniciais.

## Objetivo

Adicionar ao DjangoForge uma camada central de observabilidade capaz de responder, por sistema e ambiente:

- o que aconteceu;
- quando aconteceu;
- onde aconteceu;
- quem iniciou a operação, quando houver usuário;
- qual componente/origem produziu o evento;
- qual foi o resultado;
- quais informações técnicas ajudam a diagnosticar falhas.

A GEN-058 parte da RC validada da GEN-057.5 e complementa os contratos já existentes de `RuntimeSnapshot`, `RuntimeCheck` e `DeploymentPlan`. Ela não substitui esses modelos.

## Princípios

1. **Evento estruturado primeiro** — mensagem textual é importante, mas não é o contrato inteiro.
2. **Contexto explícito** — sistema, ambiente, usuário, origem, categoria e correlação devem ser pesquisáveis.
3. **Sem segredos** — tokens, senhas, cookies, Authorization, chaves e credenciais nunca devem ser persistidos em payloads de observabilidade.
4. **Baixo acoplamento** — serviços existentes publicam eventos sem conhecer a UI do Monitoring Center.
5. **Falha de observabilidade não quebra operação principal** — registrar log não deve transformar uma operação válida em erro funcional.
6. **Compatibilidade** — `RuntimeCheck`, `RuntimeSnapshot` e `DeploymentPlan` continuam sendo fontes especializadas de estado/histórico.
7. **Retenção controlável** — eventos operacionais não devem crescer indefinidamente.
8. **Correlação** — uma execução pode produzir vários eventos ligados pelo mesmo `correlation_id`.
9. **Auditoria não é sinônimo de log** — eventos operacionais e trilha de auditoria podem convergir na visualização, mas têm semânticas distintas.

## Escopo da GEN-058

### Incluído

- modelo persistente de evento de observabilidade;
- níveis `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`;
- categorias iniciais de eventos;
- serviço central para emissão de eventos;
- sanitização de contexto/payload;
- correlação de eventos;
- instrumentação progressiva de geração, validação, runtime e deployment;
- Monitoring Center por sistema;
- filtros por período, ambiente, nível, categoria, origem e texto;
- detalhe do evento;
- resumo operacional com contadores;
- política inicial de retenção/limpeza;
- testes de contrato, permissão, filtros, sanitização e regressão.

### Não incluído

- Elasticsearch/OpenSearch;
- Loki/Grafana;
- OpenTelemetry distribuído;
- tracing entre múltiplos serviços;
- ingestão genérica de logs externos;
- streaming em tempo real via WebSocket;
- alertas por e-mail/Slack;
- APM completo;
- métricas de infraestrutura do host;
- substituição do logging padrão do Python/Django.

Esses pontos podem evoluir depois sem quebrar o contrato estrutural desta GEN.

## Relação com modelos existentes

### RuntimeSnapshot

Representa o último estado conhecido de um ambiente. Continua sendo a fonte rápida para o estado atual.

### RuntimeCheck

Representa cada verificação de saúde executada. Continua sendo histórico especializado de health checks.

### DeploymentPlan

Representa o ciclo e estado de uma execução de deployment. Continua sendo a fonte de verdade da operação de deployment.

### ObservabilityEvent

Representa acontecimentos estruturados e correlacionáveis. Pode apontar para uma operação existente por metadados/referência, mas não duplica seu estado de domínio.

Exemplo:

- `DeploymentPlan.status = FAILED` informa o estado final do deployment;
- eventos correlacionados explicam `deployment.started`, `deployment.step`, `deployment.failed` e o diagnóstico correspondente.

## Modelo conceitual

### ObservabilityEvent

Campos propostos:

- `sistema` — FK obrigatória para `Sistema`;
- `ambiente` — FK opcional para `Ambiente`;
- `usuario` — FK opcional para usuário;
- `level` — DEBUG/INFO/WARNING/ERROR/CRITICAL;
- `category` — categoria funcional/técnica;
- `source` — componente que produziu o evento;
- `event_name` — identificador estável e legível por máquina;
- `message` — resumo legível por humano;
- `correlation_id` — UUID para agrupar eventos da mesma execução/request/operação;
- `object_type` — tipo lógico do objeto relacionado, opcional;
- `object_id` — identificador textual do objeto relacionado, opcional;
- `context` — JSON sanitizado com metadados adicionais;
- `created_at` — timestamp indexado.

Índices iniciais devem favorecer:

- sistema + data;
- sistema + nível + data;
- ambiente + data;
- correlation_id;
- category + data;
- event_name + data.

## Categorias iniciais

- `SYSTEM` — operações gerais do DjangoForge;
- `GENERATION` — geração/compilação de aplicação;
- `VALIDATION` — Validation Center e runtime validation;
- `RELEASE` — criação/validação/publicação de releases;
- `DEPLOYMENT` — execução e etapas de deployment;
- `RUNTIME` — health checks e observação de ambientes;
- `SECURITY` — eventos relevantes de autenticação/autorização, sem armazenar credenciais;
- `INTEGRATION` — integrações externas quando instrumentadas.

## Convenção de event_name

Usar nomes estáveis em minúsculas separados por ponto:

- `generation.started`
- `generation.succeeded`
- `generation.failed`
- `validation.started`
- `validation.failed`
- `release.created`
- `release.published`
- `deployment.started`
- `deployment.step.started`
- `deployment.step.succeeded`
- `deployment.failed`
- `deployment.succeeded`
- `runtime.check.started`
- `runtime.check.offline`
- `runtime.check.degraded`
- `runtime.check.healthy`

A mensagem humana pode mudar sem quebrar consumidores; `event_name` é o contrato estável.

## Serviço de emissão

Criar uma API interna única, conceitualmente:

```python
emit_event(
    *,
    sistema,
    event_name,
    message,
    level="INFO",
    category="SYSTEM",
    ambiente=None,
    usuario=None,
    correlation_id=None,
    object_type="",
    object_id="",
    context=None,
)
```

O serviço deve:

1. validar nível/categoria;
2. gerar `correlation_id` quando necessário;
3. sanitizar recursivamente o contexto;
4. persistir o evento;
5. nunca registrar valores classificados como segredo;
6. oferecer comportamento seguro caso a persistência do evento falhe.

## Sanitização

Chaves sensíveis devem ser removidas ou substituídas por `[REDACTED]`, inclusive de estruturas aninhadas.

Lista mínima:

- password;
- passwd;
- secret;
- token;
- access_token;
- refresh_token;
- authorization;
- cookie;
- api_key;
- private_key;
- database_url quando contiver credenciais.

A comparação das chaves deve ser case-insensitive e tolerar `_`/`-`.

## Correlação

`correlation_id` permite abrir uma operação e enxergar sua sequência cronológica.

Exemplo de deployment:

```text
correlation_id = 3c...91
  deployment.started
  deployment.step.started
  deployment.step.succeeded
  deployment.step.started
  deployment.failed
```

Quando existir objeto de domínio, usar também:

```text
object_type = DeploymentPlan
object_id   = 123
```

## Monitoring Center

O Workspace passa a ter, em **Run**, uma entrada clara para `Logs & Observability` / `Monitoring Center`.

### Visão principal

Deve apresentar:

- total de eventos no período;
- erros/críticos;
- warnings;
- ambientes com eventos recentes de erro;
- últimas ocorrências;
- distribuição por nível/categoria;
- filtros.

### Lista

Colunas iniciais:

- horário;
- nível;
- categoria;
- ambiente;
- evento;
- mensagem;
- usuário/origem.

Filtros:

- período;
- ambiente;
- nível;
- categoria;
- origem;
- texto/event_name.

### Detalhe

Exibir:

- metadados estruturados;
- contexto JSON sanitizado;
- objeto relacionado;
- correlation_id;
- timeline de eventos correlacionados.

## Permissões

- acesso exige autenticação;
- sistema só pode ser observado por usuário autorizado a acessá-lo;
- ações administrativas de retenção/limpeza devem ser restritas;
- nenhum endpoint de observabilidade pode permitir leitura cruzada entre sistemas sem autorização explícita.

## Retenção

Primeiro contrato:

- retenção configurável por quantidade de dias;
- default inicial: 90 dias;
- comando de manutenção para remover eventos expirados;
- limpeza deve operar em lote;
- `RuntimeSnapshot` não é afetado pela retenção de eventos;
- históricos especializados podem ter políticas próprias no futuro.

## Fases

### GEN-058.1 — Observability Core

- `ObservabilityEvent`;
- migration;
- serviço `emit_event`;
- sanitização;
- correlation_id;
- admin básico;
- testes unitários.

### GEN-058.2 — Instrumentation

Instrumentar progressivamente:

- geração;
- Validation Center/runtime validation;
- releases;
- deployment;
- runtime checks.

Não instrumentar cada view CRUD do DjangoForge nesta fase.

### GEN-058.3 — Monitoring Center

- rota e view por sistema;
- KPIs operacionais;
- filtros;
- paginação;
- detalhe;
- timeline por correlation_id;
- integração ao Workspace.

### GEN-058.4 — Retention & Hardening

- configuração de retenção;
- management command;
- proteção contra segredos;
- índices;
- limites de payload;
- testes de segurança e isolamento por sistema.

### GEN-058.5 — Regression & Manual Validation

- `python manage.py check`;
- testes específicos;
- `python manage.py test sistema`;
- validar eventos reais de geração;
- validar runtime checks;
- validar deployment quando infraestrutura permitir;
- validar filtros e detalhe;
- validar isolamento entre sistemas;
- validar que payloads sensíveis aparecem redigidos;
- congelar RC somente após validação.

## Critérios de aceite

1. Eventos possuem estrutura pesquisável, não apenas texto livre.
2. Eventos podem ser correlacionados por operação.
3. Segredos conhecidos são redigidos antes da persistência.
4. Falha na emissão de observabilidade não quebra a operação principal.
5. Runtime/Deployment continuam com seus modelos especializados.
6. Monitoring Center filtra por sistema, ambiente, nível, categoria e período.
7. Usuário não autorizado não acessa observabilidade de outro sistema.
8. Timeline correlacionada é navegável.
9. Retenção pode remover eventos antigos sem afetar snapshots atuais.
10. Nenhum recurso validado da GEN-057.5 sofre regressão.
11. Suíte anterior permanece verde.
12. Validação manual ocorre antes da promoção.

## Sequência de implementação

A implementação começa pela **GEN-058.1 — Observability Core**. Nenhuma tela do Monitoring Center deve ser criada antes do modelo, serviço, sanitização e testes do contrato central estarem estáveis.
