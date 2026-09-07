# GEN-072 — Business Workspace & Navigation

Status: **PLANEJADA / EM IMPLEMENTAÇÃO**

## Objetivo

> Permitir que o usuário organize as experiências já desenhadas no DjangoForge em espaços de trabalho orientados ao papel e ao objetivo de negócio, com navegação declarativa, segura e equivalente entre Designer, Preview e runtime gerado.

A GEN-072 parte da capacidade entregue pela GEN-071: já é possível compor uma experiência operacional rica, como uma Central do Fornecedor. O próximo problema é organizar várias dessas experiências em uma aplicação coerente para cada tipo de usuário, evitando que o sistema gerado seja apenas uma coleção de telas e menus técnicos.

## Problema que esta GEN resolve

Hoje o DjangoForge consegue definir entidades, CRUDs, formulários, dashboards, relatórios, workflows, permissões e páginas avançadas. Também consegue compor experiências relacionais de negócio.

Porém, ainda falta uma camada explícita que responda, do ponto de vista do usuário final:

```text
Quando eu entro no sistema,
qual é o meu espaço de trabalho?
O que eu vejo primeiro?
Quais experiências fazem parte do meu trabalho?
Como navego entre elas?
O que muda conforme meu papel/permissão?
```

Sem essa camada, a navegação tende a refletir artefatos técnicos em vez do fluxo de trabalho real.

## Princípio arquitetural

> Workspace organiza experiências. Não redefine as experiências que organiza.

A GEN-072 não cria uma segunda definição de página, CRUD, formulário, dashboard, relatório, workflow ou permissão.

Os Designers especializados continuam sendo donos de seus contratos. O Workspace apenas referencia destinos existentes e organiza como eles são apresentados e navegados ao usuário.

## Conceito de Workspace

Um workspace é um contrato declarativo de navegação e entrada na aplicação.

Exemplo conceitual:

```text
WORKSPACE — Gestão de Fornecedores

Início
  └── Dashboard de fornecedores

Operação
  ├── Central do Fornecedor
  ├── Fornecedores
  └── Contratos

Acompanhamento
  ├── Relatório de contratos
  └── Pendências de workflow
```

O mesmo sistema pode possuir mais de um workspace, por exemplo:

```text
Compras
Gestão de Fornecedores
Fiscalização de Contratos
Administração
```

A visibilidade final continua subordinada ao RBAC já existente.

## Fonte de verdade

A fonte de verdade continua sendo o contrato declarativo persistido da aplicação.

O contrato de workspace deve referenciar artefatos existentes por identificadores estáveis. Preview e runtime são projeções desse mesmo contrato.

Nenhum item de navegação pode conceder acesso que o RBAC não conceda.

## Escopo incluído

- contrato declarativo de `workspaces`;
- múltiplos workspaces por aplicação;
- workspace inicial/default;
- título, descrição e identidade visual mínima do workspace;
- seções/grupos de navegação;
- itens de navegação que referenciam destinos existentes;
- destinos iniciais suportados: CRUD/listagem, dashboard, relatório, workflow quando navegável e Advanced Page;
- ordenação explícita de seções e itens;
- item inicial/home do workspace;
- visibilidade derivada do RBAC existente;
- remoção fail-closed de destinos inválidos ou não autorizados;
- Preview do workspace dentro do Application Preview Studio;
- geração/runtime da navegação equivalente ao contrato;
- deep links estáveis para destinos declarados;
- breadcrumbs/contexto de navegação quando aplicável;
- equivalência Designer → contrato → Preview → geração → runtime;
- teste end-to-end com pelo menos dois papéis percebendo workspaces/navegação compatíveis com suas permissões.

## Escopo não incluído

- redefinição das permissões do Permission Designer;
- criação de CRUDs, páginas, relatórios, dashboards ou workflows dentro do Workspace Designer;
- menu livre baseado em URL arbitrária;
- URLs externas arbitrárias na primeira versão;
- regras Python/JavaScript fornecidas pelo usuário;
- personalização individual por usuário final;
- favoritos pessoais;
- histórico de navegação pessoal;
- mecanismo de busca global da aplicação;
- command palette;
- portal multiaplicação entre sistemas diferentes.

Essas capacidades podem ser avaliadas em GENs posteriores.

## Contrato canônico inicial

Representação conceitual inicial:

```json
{
  "workspaces": [
    {
      "id": "gestao_fornecedores",
      "label": "Gestão de Fornecedores",
      "description": "Operação e acompanhamento de fornecedores e contratos",
      "default": true,
      "home": {
        "kind": "dashboard",
        "ref": "dashboard_fornecedores"
      },
      "sections": [
        {
          "id": "operacao",
          "label": "Operação",
          "items": [
            {
              "id": "central_fornecedor",
              "label": "Central do Fornecedor",
              "target": {
                "kind": "advanced_page",
                "ref": "central_fornecedor"
              }
            },
            {
              "id": "fornecedores",
              "label": "Fornecedores",
              "target": {
                "kind": "crud",
                "entity": "Fornecedor",
                "operation": "list"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

A forma final pode evoluir durante a GEN, mas deve preservar a semântica: o usuário escolhe experiências de negócio conhecidas; não configura URLs Django.

## Regras de segurança e consistência

1. Todo destino deve existir no contrato da aplicação.
2. Todo destino deve ser navegável no contexto declarado.
3. A existência de um item no workspace não concede permissão.
4. O runtime deve avaliar o RBAC original do destino.
5. Destino inválido ou não autorizado deve falhar fechado.
6. Um `home` invisível ao usuário não pode quebrar o workspace; deve existir resolução segura para o primeiro destino autorizado, ou uma experiência vazia explícita.
7. Preview e runtime devem usar as mesmas regras de resolução de visibilidade.
8. Nenhuma URL Django manual deve ser persistida como fonte de verdade do workspace.

## Caso de prova oficial

O cenário de validação será uma aplicação com dois papéis:

```text
Gestor de Fornecedores
Fiscal de Contratos
```

E experiências já existentes, como:

```text
Dashboard de Fornecedores
Central do Fornecedor
CRUD de Fornecedores
CRUD de Contratos
Relatório de Contratos
Workflow de Contratos
```

Resultado esperado:

```text
Gestor de Fornecedores
  → workspace Gestão de Fornecedores
  → vê dashboard, central, fornecedores, contratos e relatórios permitidos

Fiscal de Contratos
  → workspace Fiscalização
  → vê somente experiências compatíveis com suas permissões
```

O teste deve demonstrar que navegação e visibilidade são derivadas do contrato e do RBAC, não de menus codificados manualmente.

## Roadmap

### GEN-072.1 — Contrato de Workspace

Definir schema, normalização, IDs estáveis, home, seções, itens e referências de destino.

### GEN-072.2 — Validação semântica de destinos

Resolver referências contra os contratos existentes e rejeitar destinos inexistentes, incompatíveis ou não navegáveis.

### GEN-072.3 — Workspace Designer

Criar a experiência de configuração orientada ao negócio: criar workspace, ordenar seções e escolher experiências existentes como itens.

### GEN-072.4 — RBAC e visibilidade derivada

Aplicar permissões existentes sobre itens e home sem criar uma camada paralela de autorização.

### GEN-072.5 — Preview do Workspace

Projetar shell, home, seções, itens e estados de visibilidade no Application Preview Studio.

### GEN-072.6 — Runtime gerado

Gerar navegação real, resolução de home e destinos a partir do contrato compilado.

### GEN-072.7 — Deep links e breadcrumbs

Preservar navegação contextual e URLs estáveis entre experiências declaradas.

### GEN-072.8 — Multi-workspace por papel

Validar seleção e disponibilidade de workspaces coerentes para diferentes perfis/permissões.

### GEN-072.9 — Equivalência end-to-end

Criar gate transversal Designer → contrato → Preview → geração → runtime.

### GEN-072.10 — Freeze

Executar regressão completa, registrar baseline segura e incorporar a GEN concluída à `master`.

## Critério de sucesso da GEN

A GEN-072 será considerada bem-sucedida quando o usuário conseguir organizar experiências existentes em um ou mais workspaces sem configurar URLs ou Django, e o sistema gerado apresentar a mesma navegação, home e visibilidade observadas no Designer/Preview, respeitando integralmente o RBAC já definido.

O critério não é apenas "ter um menu configurável".

O critério é entregar uma aplicação que pareça organizada pelo trabalho do usuário, e não pela estrutura técnica do projeto.

## Changelog

### 2026-09-07 — criação da GEN-072

**Decisão:** iniciar a GEN-072 como **Business Workspace & Navigation**.

**Motivo:** após a GEN-071 provar composição de experiências operacionais, o próximo nível de produto é organizar múltiplas experiências em espaços de trabalho coerentes, orientados ao papel e ao objetivo do usuário final.

**Impacto:** o DjangoForge passa a evoluir da composição de uma tela de negócio para a composição da jornada de navegação dentro da aplicação, preservando Designers especializados, contrato declarativo único e RBAC existente.
