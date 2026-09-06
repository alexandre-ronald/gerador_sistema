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

## Marco atual

### GEN-070 — Advanced Page Designer

Status: **PLANEJADA / EM INÍCIO DE IMPLEMENTAÇÃO**

Objetivo:

> Permitir montar páginas e experiências de negócio além do CRUD padrão, mantendo o mesmo contrato declarativo como fonte de verdade e garantindo que aquilo que é desenhado, visualizado e gerado tenha comportamento equivalente no runtime.

A GEN-070 incorpora a necessidade anteriormente identificada como **Runtime Contract Enforcement**. Essa responsabilidade não será tratada como uma GEN separada neste momento; ela passa a fazer parte do Advanced Page Designer porque páginas avançadas só são válidas se permissões, ações, relatórios, workflows, navegação e demais contratos forem respeitados também no runtime gerado.

Arquivo detalhado:

```text
docs/GEN-070-advanced-page-designer.md
```

Branch de trabalho:

```text
gen-070-advanced-page-designer
```

Base de partida:

```text
gen-069-regression-safe-baseline-final
574fa04baf9fdce67a145a79e647b81900f4b9dd
```

## Direção após a GEN-070

Os marcos posteriores serão oficializados neste arquivo antes de sua implementação. Não há numeração futura considerada definitiva enquanto não estiver registrada aqui.

## Changelog de planejamento

### 2026-09-06 — criação do roadmap oficial

**Decisão:** criar um roadmap versionado no Git como referência formal do planejamento do projeto.

**Motivo:** evitar perda de contexto entre conversas, implementação e evolução arquitetural.

**Impacto:** toda mudança futura de escopo deve ser documentada aqui e no documento específico da GEN correspondente.

### 2026-09-06 — consolidação da GEN-070

**Decisão:** manter a GEN-070 como **Advanced Page Designer** e incorporar nela o escopo de **Runtime Contract Enforcement**.

**Motivo:** páginas e experiências avançadas não devem formar um runtime paralelo nem ignorar contratos já definidos pelos Designers.

**Impacto:** a GEN-070 passa a incluir tanto composição avançada de páginas quanto enforcement de contratos no runtime gerado, com testes de equivalência entre Designer, Preview e Runtime.
