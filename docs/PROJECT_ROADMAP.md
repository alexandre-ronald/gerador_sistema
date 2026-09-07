# DjangoForge — Roadmap oficial do projeto

## Propósito deste documento

Este arquivo é a referência oficial do planejamento evolutivo do DjangoForge.

A partir da GEN-070, todo marco relevante do projeto deve estar registrado aqui antes ou junto da implementação correspondente.

Mudanças de escopo não devem existir apenas em conversa, memória de equipe ou código. Qualquer alteração material de objetivo, fronteira, responsabilidade ou sequência de uma GEN deve ser refletida neste documento e no arquivo específico da GEN afetada.

## Regra de governança de escopo

Para cada GEN:

1. o objetivo deve ser registrado antes da implementação estrutural;
2. o escopo incluído e não incluído deve estar explícito;
3. mudanças materiais devem atualizar a documentação no mesmo ciclo de trabalho em que forem decididas;
4. toda mudança de escopo deve ser registrada em um changelog com data, decisão, motivo e impacto;
5. uma GEN só pode ser considerada congelada após testes de regressão e criação de baseline segura;
6. o código não substitui o planejamento: a documentação define a intenção, e o código implementa essa intenção.

## Princípio arquitetural permanente

> O usuário nunca configura Django. Ele configura o comportamento da aplicação.

Fluxo conceitual:

```text
Intenção do usuário
        ↓
Designers especializados
        ↓
Contrato declarativo persistido
        ↓
Normalização e validação
        ↓
Preview / Blueprint
        ↓
Geração e runtime Django
```

Blueprint e Preview são projeções. Não são fontes paralelas de verdade.

## Marcos recentes

### GEN-067 — Permission Designer 2.0

Status: **CONCLUÍDA / CONGELADA**

Responsabilidade principal: configuração de papéis, capacidades CRUD, ações de workflow e evolução do RBAC orientado ao negócio.

### GEN-068 — Application Blueprint

Status: **CONCLUÍDA / CONGELADA**

Responsabilidade principal: consolidar visualmente o que existe na aplicação desenhada.

### GEN-069 — Application Preview Studio

Status: **CONCLUÍDA / CONGELADA**

Baseline final:

```text
574fa04baf9fdce67a145a79e647b81900f4b9dd
```

Responsabilidade principal: projetar visualmente a experiência resultante dos contratos existentes, incluindo shell, listagens, formulários, dashboard, relatórios, workflow, RBAC, dispositivos e navegação Preview ↔ Designers.

### GEN-070 — Advanced Page Designer

Status: **CONCLUÍDA / CONGELADA**

Objetivo:

> Permitir montar páginas e experiências de negócio além do CRUD padrão, mantendo o mesmo contrato declarativo como fonte de verdade e garantindo que aquilo que é desenhado, visualizado e gerado tenha comportamento equivalente no runtime.

Responsabilidade principal: composição de páginas e experiências além do CRUD, layout declarativo em 12 colunas, componentes e bindings, ações de processo, integração com Preview Studio, runtime de páginas avançadas e Runtime Contract Enforcement para CRUD, workflow, relatórios, navegação e ações aplicáveis.

A GEN-070 preserva os Designers especializados como donos de seus contratos. O Advanced Page Designer compõe essas capacidades; não redefine Form, CRUD, Report, Dashboard, Workflow ou Permission Designer.

Gate final de regressão em 2026-09-06:

```text
python manage.py check
python manage.py test
```

Ambos reportados verdes pelo usuário após o gate transversal de equivalência Contrato → Preview → geração → runtime.

Arquivo detalhado:

```text
docs/GEN-070-advanced-page-designer.md
```

### GEN-071 — Business Experience Composition

Status: **CONCLUÍDA / CONGELADA**

Objetivo:

> Transformar o Advanced Page Designer em uma ferramenta capaz de compor experiências operacionais reais de negócio, combinando um registro principal com dados relacionados, indicadores, listas, relatórios e ações, sem exigir programação Django pelo usuário.

Responsabilidade principal: composição relacional de páginas orientadas ao trabalho, com bindings entre contexto e entidades relacionadas, coleções relacionadas, métricas declarativas, transporte de contexto, Preview fiel e runtime equivalente.

Caso de prova oficial: **Central do Fornecedor**.

Gate final em 2026-09-07:

```text
python manage.py test sistema
```

Regressão completa reportada verde pelo usuário.

Baseline final:

```text
424dd57e284eaba1577239c8238d31c1a298560d
```

Arquivo detalhado:

```text
docs/GEN-071-business-experience-composition.md
```

Branch histórica:

```text
gen-071-business-experience-composition
```

A GEN-071 foi incorporada à `master` após o freeze.

### GEN-072 — Business Workspace & Navigation

Status: **PLANEJADA / EM IMPLEMENTAÇÃO**

Objetivo:

> Permitir que o usuário organize as experiências já desenhadas no DjangoForge em espaços de trabalho orientados ao papel e ao objetivo de negócio, com navegação declarativa, segura e equivalente entre Designer, Preview e runtime gerado.

Responsabilidade principal: contrato de workspaces, home, seções e itens de navegação referenciando capacidades existentes, visibilidade derivada do RBAC, Preview, runtime, deep links, breadcrumbs e equivalência end-to-end.

Princípio:

> Workspace organiza experiências. Não redefine as experiências que organiza.

Arquivo detalhado:

```text
docs/GEN-072-business-workspace-navigation.md
```

Branch de implementação:

```text
gen-072-business-workspace-navigation
```

Base de partida:

```text
master
```

## Próximo marco

GEN-072 em execução. Nenhuma GEN posterior é considerada definitiva até que objetivo, escopo e fronteiras sejam registrados neste arquivo antes da implementação estrutural.

## Changelog de planejamento

### 2026-09-06 — criação do roadmap oficial

**Decisão:** criar um roadmap versionado no Git como referência formal do planejamento do projeto.

**Motivo:** evitar perda de contexto entre conversas, implementação e evolução arquitetural.

**Impacto:** toda mudança futura de escopo deve ser documentada aqui e no documento específico da GEN correspondente.

### 2026-09-06 — consolidação da GEN-070

**Decisão:** manter a GEN-070 como **Advanced Page Designer** e incorporar nela o escopo de **Runtime Contract Enforcement**.

**Motivo:** páginas e experiências avançadas não devem formar um runtime paralelo nem ignorar contratos já definidos pelos Designers.

**Impacto:** a GEN-070 passa a incluir tanto composição avançada de páginas quanto enforcement de contratos no runtime gerado, com testes de equivalência entre Designer, Preview e Runtime.

### 2026-09-06 — conclusão e freeze da GEN-070

**Decisão:** encerrar a GEN-070 após conclusão das fases 070.1 a 070.10, gate transversal de equivalência e regressão completa.

**Motivo:** os contratos, Designer, Preview, geração, runtime e enforcement foram validados em conjunto e a suíte completa permaneceu verde.

**Impacto:** a GEN-070 passa a ser baseline histórica congelada. Novas capacidades devem ser planejadas em um novo marco, sem ampliar silenciosamente o escopo desta GEN.

### 2026-09-06 — criação da GEN-071

**Decisão:** iniciar a GEN-071 como **Business Experience Composition**.

**Motivo:** a infraestrutura da GEN-070 permite páginas avançadas, mas o valor para o usuário precisa ser provado com experiências operacionais que combinem um registro principal e capacidades relacionadas em uma única tela de trabalho.

**Impacto:** o ciclo passa a priorizar bindings relacionais seguros, coleções relacionadas, métricas e transporte de contexto, culminando numa Central do Fornecedor end-to-end sem código manual específico no gerador.

### 2026-09-07 — conclusão e freeze da GEN-071

**Decisão:** encerrar a GEN-071 após validação dos gates direcionados, regressão completa do app `sistema` e registro da baseline final.

**Motivo:** Designer, contrato relacional, Preview, geração, runtime e RBAC foram validados conjuntamente, incluindo seleção contextual do Preview.

**Impacto:** a GEN-071 torna-se baseline histórica congelada e é incorporada à `master` no commit `424dd57e284eaba1577239c8238d31c1a298560d`.

### 2026-09-07 — criação da GEN-072

**Decisão:** iniciar a GEN-072 como **Business Workspace & Navigation**.

**Motivo:** após a composição de experiências individuais estar madura, o próximo problema de produto é organizar múltiplas experiências em jornadas e espaços de trabalho coerentes para diferentes papéis.

**Impacto:** o DjangoForge passa a modelar também a entrada e a navegação da aplicação sem introduzir URLs Django manuais nem uma camada paralela de autorização.
