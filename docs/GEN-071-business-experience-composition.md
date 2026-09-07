# GEN-071 — Business Experience Composition

Status: **CONCLUÍDA / CONGELADA**

## Objetivo

> Transformar o Advanced Page Designer em uma ferramenta capaz de compor experiências operacionais reais de negócio, combinando um registro principal com dados relacionados, indicadores, listas, relatórios e ações, sem exigir que o usuário programe Django.

A GEN-071 existe para provar o valor prático da composição avançada por meio de páginas orientadas ao trabalho do usuário, e não apenas às entidades isoladas.

## Problema que esta GEN resolve

A GEN-070 criou o contrato, o Designer, o Preview e o runtime de páginas avançadas. Porém, uma página composta apenas por campos do próprio registro ainda pode parecer pouco diferente de um CRUD ou Form Designer.

A GEN-071 deve permitir experiências como uma **Central do Fornecedor**:

```text
Fornecedor atual
    ├── dados principais
    ├── KPIs derivados
    ├── contratos relacionados
    ├── relatórios relacionados
    ├── ações de CRUD
    └── ações de workflow
```

O objetivo é permitir que o usuário modele uma tela de trabalho completa sem escrever views, queries ou templates manualmente.

## Princípio arquitetural

> O Advanced Page Designer compõe experiências. Os Designers especializados continuam sendo donos das capacidades que ele referencia.

A GEN-071 não cria uma segunda definição de CRUD, Form, Report, Dashboard, Workflow ou RBAC.

## Caso de uso de referência

O caso de prova da GEN-071 será **Central do Fornecedor**.

Entidade principal:

```text
Fornecedor
```

Experiência esperada:

```text
CENTRAL DO FORNECEDOR

Fornecedor                       Situação
Hospitalar Nordeste              Ativo

Contratos ativos                 Total contratado
7                                R$ 2.840.000

CONTRATOS DO FORNECEDOR
[tabela relacionada filtrada pelo fornecedor atual]

RELATÓRIOS
[relatórios vinculados ao fornecedor]

AÇÕES
[Editar fornecedor] [Novo contrato] [Ação de workflow]
```

A implementação deve ser genérica. O caso Fornecedor/Contrato é somente o cenário de validação.

## Escopo incluído

- bindings relacionais entre o contexto atual da página e entidades relacionadas;
- componente de coleção relacionada;
- filtros declarativos baseados no registro de contexto;
- métricas derivadas de coleções relacionadas;
- ações que transportam contexto entre páginas e CRUDs;
- Preview demonstrativo fiel ao contrato relacional;
- geração/runtime das relações configuradas;
- enforcement de RBAC também sobre dados, ações e destinos relacionados;
- equivalência Designer → Preview → geração → runtime;
- teste funcional de uma Central do Fornecedor composta sem código manual.

## Escopo não incluído

- editor visual de consultas SQL;
- linguagem livre de SQL, Python ou JavaScript fornecida pelo usuário;
- substituição do ORM Django por uma query language própria;
- redefinição de relacionamentos de modelo já pertencentes ao domínio;
- criação de workflows, relatórios ou formulários dentro do Advanced Page Designer;
- joins arbitrários sem caminho relacional conhecido pelo contrato/modelo;
- BI ou analytics ad hoc de propósito geral.

## Fonte de verdade

A fonte de verdade continua sendo o contrato declarativo persistido da aplicação.

A GEN-071 pode evoluir o contrato `advanced_pages`, mas referências relacionais devem usar IDs/nomes estáveis e relações já conhecidas pelo modelo da aplicação.

Preview e runtime são projeções do mesmo contrato.

## Roadmap

### GEN-071.1 — Modelo relacional de bindings

Status: **IMPLEMENTADA / VALIDADA**

Definir contrato, normalização, validação e semântica para relacionar o contexto atual a outras entidades.

Critério mínimo:

```text
Página record: Fornecedor
       ↓
relação declarativa
       ↓
Contrato.fornecedor = contexto.pk
```

Representação canônica inicial:

```json
{
  "binding": {"kind": "entity", "ref": "Contrato", "field": ""},
  "config": {
    "relation": {
      "source": "page_context",
      "source_field": "pk",
      "target_field": "fornecedor"
    }
  }
}
```

A validação é fail-closed: a página deve ser `record`, o destino deve ser uma entidade conhecida, `target_field` deve existir, ser relacional e apontar para a entidade do contexto. Lookup livre (`__`), SQL e caminhos arbitrários não são aceitos.

Gate reportado verde pelo usuário em 2026-09-06.

### GEN-071.2 — Related Collection Component

Status: **IMPLEMENTADA / VALIDADA**

Permitir uma tabela/lista relacionada ao registro atual.

Exemplo:

```text
Fornecedor atual → Contratos deste fornecedor
```

O Page Designer oferece **Tabela relacionada** somente de forma compatível com o contrato relacional da GEN-071.1. Em uma página `record`, ele descobre campos relacionais que apontam para a entidade de contexto, cria a tabela com `config.relation` e permite escolher o campo de relação no inspector. O Preview identifica visualmente a coleção relacionada e mostra a regra declarativa aplicada.

Gate e teste visual reportados verdes pelo usuário em 2026-09-06.

### GEN-071.3 — Métricas relacionais

Status: **IMPLEMENTADA / VALIDADA**

Permitir métricas derivadas de uma coleção relacionada, inicialmente com operações seguras e declarativas:

```text
count
sum
avg
min
max
```

Representação canônica:

```json
{
  "type": "metric",
  "binding": {"kind": "entity", "ref": "Contrato", "field": ""},
  "config": {
    "relation": {
      "source": "page_context",
      "source_field": "pk",
      "target_field": "fornecedor"
    },
    "aggregate": {
      "operation": "sum",
      "field": "valor"
    }
  }
}
```

`count` não exige campo. `sum` e `avg` aceitam apenas campos numéricos. `min` e `max` aceitam campos numéricos ou temporais diretamente conhecidos pelo domínio. Expressões, funções arbitrárias e lookups livres permanecem proibidos.

O Page Designer oferece **Métrica relacionada** e permite configurar cálculo e campo. O Preview projeta valor demonstrativo coerente e mantém a origem relacional explícita.

Gate e teste visual reportados verdes pelo usuário em 2026-09-06.

### GEN-071.4 — Ações com transporte de contexto

Status: **IMPLEMENTADA / VALIDADA**

Permitir que ações levem o contexto atual para CRUDs ou outras páginas.

Primeira fatia funcional desta etapa: uma ação CRUD `create`, originada de uma página `record`, pode transportar `page_context.pk` para um campo relacional da entidade criada.

Exemplo:

```text
Novo contrato
    ↓
CRUD create de Contrato
    ↓
Contrato.fornecedor ← Fornecedor atual
```

Representação canônica:

```json
{
  "id": "novo_contrato",
  "kind": "crud",
  "label": "Novo contrato",
  "target": {"entity": "Contrato", "operation": "create"},
  "transport": {
    "source": "page_context",
    "source_field": "pk",
    "target_field": "fornecedor"
  }
}
```

A validação é fail-closed: nesta fase o transporte exige `crud/create`, página `record`, campo relacional conhecido e relação apontando para a entidade do contexto. O Designer expõe a opção **Levar contexto atual para o novo registro** e permite escolher o vínculo compatível.

Gate e teste visual reportados verdes pelo usuário em 2026-09-06.

### GEN-071.5 — Preview da experiência composta

Status: **IMPLEMENTADA / VALIDADA**

Projetar coleções, métricas e ações relacionais no Preview Studio com dados demonstrativos coerentes.

O Preview reúne agora, na mesma página avançada, a coleção relacionada, métricas derivadas e ações vinculadas. Métricas relacionais mostram operação/origem; coleções mantêm a regra de relação; ações CRUD `create` com transporte exibem explicitamente o vínculo que será preenchido no runtime, por exemplo `Contrato.fornecedor ← Fornecedor atual`.

A projeção continua somente leitura e demonstrativa. A execução real das consultas e do transporte de contexto pertence à GEN-071.6.

Gate reportado verde pelo usuário em 2026-09-07.

### GEN-071.6 — Runtime gerado

Status: **IMPLEMENTADA / VALIDADA**

Gerar consultas ORM seguras a partir do contrato relacional normalizado.

O gerador compila nomes de campos do contrato para identificadores Python antes de emitir o runtime. Coleções relacionadas usam filtro pelo registro atual; métricas usam somente `count`, `sum`, `avg`, `min` e `max`; ações de criação transportam o contexto por parâmetro compilado e o formulário gerado reconhece apenas vínculos previamente declarados pelo contrato.

Gate reportado verde pelo usuário em 2026-09-07.

### GEN-071.7 — Runtime Contract Enforcement relacional

Status: **IMPLEMENTADA / VALIDADA**

Aplicar RBAC, contexto e validação fail-closed também aos componentes e ações relacionais.

A relação não cria uma permissão paralela. Uma coleção ou métrica relacionada exige acesso à página de origem e permissão `list` explícita na entidade relacionada. Uma ação com transporte exige acesso ao registro de origem e a permissão original `create` da entidade de destino. Relações e transportes incompletos, fora de contexto `record`, com fonte inválida ou com sintaxe de lookup livre são rejeitados em modo fail-closed.

Gate reportado verde pelo usuário em 2026-09-07.

### GEN-071.8 — Central do Fornecedor end-to-end

Status: **IMPLEMENTADA / VALIDADA**

Montar e validar o caso de referência sem escrever código específico de negócio no gerador.

O gate automatizado da etapa usa uma única configuração declarativa da Central do Fornecedor e verifica conjuntamente: duas métricas relacionadas (`count` e `sum`), coleção de contratos filtrada pelo fornecedor atual, ação `Novo contrato` com transporte de contexto e enforcement RBAC sobre os dados e a ação relacionados.

A validação end-to-end comprovou a composição relacional como uma única experiência de negócio, sem introduzir código específico de Fornecedor/Contrato no gerador.

### GEN-071.9 — Equivalência e regressão

Status: **IMPLEMENTADA / VALIDADA**

Gate transversal Designer → contrato persistido → Preview → geração → runtime validado.

A equivalência protege tanto a representação declarativa quanto a projeção compilada consumida pelo runtime. O gate também cobre entrada contextual no Advanced Page Designer e preservação da página selecionada ao abrir o Preview Studio.

### GEN-071.10 — Freeze

Status: **CONCLUÍDA / CONGELADA**

Regressão direcionada e regressão completa do app `sistema` executadas com sucesso, seguidas de `manage.py check` sem problemas reportados.

A baseline congelada inclui o contrato relacional, componentes relacionados, métricas, transporte de contexto, Preview, runtime gerado, RBAC relacional, Central do Fornecedor end-to-end e equivalência Designer → Preview → geração → runtime.

## Critério de sucesso da GEN

A GEN-071 só será considerada bem-sucedida se o usuário conseguir montar uma experiência como **Central do Fornecedor** usando o DjangoForge e o sistema gerado reproduzir essa experiência com comportamento coerente.

O critério não é apenas "o contrato aceita relações". O critério é o valor entregue ao usuário final.

**Critério atendido em 2026-09-07.**

## Changelog

### 2026-09-06 — criação da GEN-071

**Decisão:** criar a GEN-071 como Business Experience Composition.

**Motivo:** a GEN-070 provou a infraestrutura de páginas avançadas, mas a composição precisa demonstrar valor real por meio de experiências que combinem um registro principal com informações e capacidades relacionadas.

**Impacto:** o próximo ciclo passa a priorizar composição relacional e uma prova end-to-end de Central do Fornecedor, sem ampliar silenciosamente a GEN-070 congelada.

### 2026-09-06 — implementação da GEN-071.1

**Decisão:** representar a primeira relação segura em `component.config.relation`, mantendo o binding de entidade existente e compatibilidade com o contrato da GEN-070.

**Motivo:** permitir `Contrato.fornecedor = page_context.pk` sem introduzir SQL, lookup ORM arbitrário ou uma segunda fonte de verdade.

**Impacto:** a validação semântica passa a conhecer metadados de tipo e entidade relacionada dos campos e rejeita relações incompatíveis antes de Preview/geração/runtime.

### 2026-09-06 — validação da GEN-071.1 e implementação da GEN-071.2

**Decisão:** considerar a GEN-071.1 validada após gate reportado verde pelo usuário e expor a primeira experiência visual de coleção relacionada no Advanced Page Designer.

**Motivo:** o valor da composição precisa ser configurável pelo usuário, não apenas representável no contrato.

**Impacto:** páginas `record` passam a poder adicionar uma tabela relacionada a partir das relações conhecidas do domínio, com filtro declarativo pelo contexto atual e representação correspondente no Preview Studio.

### 2026-09-06 — validação da GEN-071.2 e implementação da GEN-071.3

**Decisão:** considerar a coleção relacionada validada após gate verde e adicionar agregações relacionais declarativas sobre a mesma relação segura.

**Motivo:** uma experiência operacional precisa resumir a coleção relacionada em KPIs sem exigir consultas manuais.

**Impacto:** páginas `record` passam a poder exibir contagem, soma, média, mínimo e máximo de registros relacionados, com validação de tipo e Preview demonstrativo coerente.

### 2026-09-06 — validação visual da GEN-071.3 e implementação da GEN-071.4

**Decisão:** considerar métricas relacionais validadas após gate e teste visual verdes e iniciar transporte de contexto por ações CRUD de criação.

**Motivo:** a composição só se torna operacional quando uma ação iniciada no contexto atual consegue criar dados relacionados sem exigir que o usuário repita manualmente o vínculo.

**Impacto:** ações `crud/create` podem declarar de forma segura que a chave do registro atual preencherá um campo relacional do novo registro; o Page Designer passa a configurar esse transporte sem código.

### 2026-09-06 — validação da GEN-071.4 e correção do feedback de salvamento

**Decisão:** considerar a GEN-071.4 validada após gate e teste visual verdes e tornar o feedback de salvamento inequívoco.

**Motivo:** a mensagem de sucesso permanecia na tela entre salvamentos, tornando impossível distinguir uma confirmação antiga de um novo salvamento.

**Impacto:** ao salvar, a confirmação anterior é removida imediatamente, o botão entra em estado `Salvando...`, a confirmação inclui horário do salvamento e a mensagem de sucesso some automaticamente após alguns segundos.

### 2026-09-06 — implementação da GEN-071.5

**Decisão:** consolidar no Preview Studio a leitura conjunta dos contratos relacionais já validados nas etapas 071.2, 071.3 e 071.4.

**Motivo:** o valor da composição deve ser perceptível como uma experiência única, e não como recursos isolados do Designer.

**Impacto:** o Preview passa a identificar a origem de métricas relacionais e o transporte de contexto de ações, mantendo a tabela relacionada e respeitando a mesma projeção/RBAC já existente. A execução permanece reservada ao runtime da GEN-071.6.

### 2026-09-07 — validação da GEN-071.5 e GEN-071.6

**Decisão:** considerar Preview composto e runtime relacional validados após gates reportados verdes pelo usuário.

**Motivo:** a experiência deixou de ser apenas demonstrativa: o contrato passou a compilar filtros, agregações e transporte de contexto para o sistema gerado.

**Impacto:** a próxima etapa passa a tratar explicitamente o enforcement relacional, mantendo RBAC e contexto como requisitos derivados das capacidades originais.

### 2026-09-07 — implementação e validação da GEN-071.7

**Decisão:** fazer componentes e ações relacionais reutilizarem as permissões CRUD existentes, com validação contextual fail-closed, e considerar a etapa validada após gate reportado verde pelo usuário.

**Motivo:** uma relação não pode ampliar permissões. Visualizar o fornecedor não implica poder listar contratos, e transportar o fornecedor para um novo contrato não implica permissão para criar contratos.

**Impacto:** coleções/métricas relacionais exigem `list` da entidade relacionada; ações transportadas preservam a autorização original da ação; configurações relacionais incompletas ou incompatíveis são negadas antes do runtime.

### 2026-09-07 — início da GEN-071.8

**Decisão:** consolidar o caso Central do Fornecedor em um gate transversal próprio antes da validação manual do sistema gerado.

**Motivo:** a GEN-071 deve provar uma experiência de negócio completa, e não somente a soma de testes unitários das capacidades isoladas.

**Impacto:** uma mesma configuração de referência passa a atravessar compilação, runtime relacional, transporte de contexto e RBAC.

### 2026-09-07 — validação da GEN-071.8 e GEN-071.9

**Decisão:** considerar a Central do Fornecedor e o gate transversal de equivalência validados após os testes end-to-end e direcionados reportados verdes.

**Motivo:** o caso de referência passou a comprovar numa única experiência métricas, coleção relacionada, transporte de contexto, RBAC e equivalência entre as projeções do contrato.

**Impacto:** a GEN-071 ficou apta a entrar em freeze, restando apenas a regressão completa da baseline.

### 2026-09-07 — correção de seleção contextual do Preview

**Decisão:** restaurar o transporte explícito da página Advanced selecionada entre o Designer e o Preview Studio.

**Motivo:** a regressão completa revelou que o wrapper contextual era carregado, porém a URL do Preview não preservava o contrato `pagina=advanced` + `pagina_avancada=<pageId>` esperado pelo fluxo contextual.

**Impacto:** o gate `test_page_designer_preview_selection` voltou a ficar verde e a seleção da página passou novamente a ser preservada no Preview. Correção registrada no commit `a452dda`.

### 2026-09-07 — freeze da GEN-071

**Decisão:** encerrar a GEN-071 como **CONCLUÍDA / CONGELADA** após regressão direcionada, `manage.py check` e regressão completa do app `sistema` reportados verdes pelo usuário.

**Motivo:** todas as etapas 071.1–071.10 estão validadas e a composição de experiência de negócio possui cobertura transversal do Designer ao runtime.

**Impacto:** a baseline da GEN-071 passa a ser tratada como estável. Evoluções futuras devem entrar em uma nova GEN e não ampliar silenciosamente o escopo congelado.
