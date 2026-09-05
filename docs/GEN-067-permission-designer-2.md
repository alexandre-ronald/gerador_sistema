# GEN-067 — Permission Designer 2.0

## Objetivo

Permitir que o usuário defina **quem pode fazer o quê** usando a linguagem do negócio, sem precisar compreender RBAC, Django Groups, codenames de permissões ou detalhes de implementação.

Princípio de produto:

> O usuário descreve responsabilidades e ações permitidas. O DjangoForge materializa autorização Django/RBAC no sistema gerado.

## Filosofia

1. intenção antes de implementação;
2. linguagem de negócio antes de linguagem Django;
3. Designer antes de infraestrutura;
4. resultado visível antes de abstração técnica.

O contrato técnico continua explícito, determinístico, validado e fail-closed. A mudança está na experiência oferecida ao usuário.

## Roadmap

- GEN-067.1 — Papéis orientados ao negócio ✅
- GEN-067.2 — Capacidades em vez de CRUD técnico ✅
- GEN-067.3 — Ações de Workflow ✅
- GEN-067.4 — Visão por papel ✅
- GEN-067.5 — Visão por funcionalidade ✅
- GEN-067.6 — Explicação de acesso ✅
- GEN-067.7 — Testes, regressão e freeze ✅

## GEN-067.1 — Papéis orientados ao negócio

O usuário informa nome e descrição da responsabilidade. IDs técnicos e Django Groups permanecem internos. Configurações antigas com `group` explícito preservam esse valor; novos papéis podem derivar o grupo interno de `label`. IDs permanecem estáveis.

## GEN-067.2 — Capacidades em vez de CRUD técnico

A interface traduz o contrato CRUD estável para capacidades orientadas ao negócio:

```text
Consultar registros -> list
Ver detalhes        -> view
Cadastrar novo      -> create
Alterar registros   -> update
Excluir registros   -> delete
```

A persistência continua usando os mesmos IDs técnicos.

## GEN-067.3 — Ações de Workflow

O Workflow Designer continua sendo a fonte das ações possíveis do processo. O Permission Designer apenas responde **quem pode executá-las**. Nenhuma transição é duplicada ou redefinida.

## GEN-067.4 — Visão por papel

Permite escolher um papel e compreender rapidamente tudo o que ele pode fazer. A visão é derivada de `rbac.roles`, `rbac.entities[*].roles` e `rbac.entities[*].transitions`, sem persistência própria. `selectedRoleId` é apenas estado transitório de interface.

## GEN-067.5 — Visão por funcionalidade

Inverte a perspectiva da `.4`: para uma informação, mostra quais papéis podem executar cada capacidade e cada ação do processo.

```text
Pedido
  Consultar registros -> Operador, Gestor
  Alterar registros   -> Gestor
  Aprovar              -> Gestor
```

A visão usa exatamente o mesmo contrato RBAC. `selectedFeatureName` é transitório e não é persistido.

## GEN-067.6 — Explicação de acesso

Permite responder, em linguagem de negócio, **por que uma autorização está permitida ou bloqueada**.

```text
Papel + Informação + Capacidade/Ação
                ↓
         Explicação de acesso
```

`explainAccess()` consulta diretamente `rbac.roles`, `rbac.entities[entidade].roles[papel]`, `rbac.entities[entidade].transitions[ação]` e `workflows[entidade]`. Não existe política paralela, cache de autorização ou nova persistência.

A GEN-067.6 explica o contrato por papel. Ela não inventa vínculo entre usuários reais e papéis porque esse vínculo não pertence ao contrato atual do Designer.

## GEN-067.7 — Regressão e freeze

### Gate executado

A conclusão do ciclo foi condicionada ao gate completo:

```text
python manage.py check
python manage.py test sistema.test_rbac_ui
python manage.py test sistema.test_rbac
python manage.py test
```

O gate foi validado pelo usuário em 2026-09-05 com todos os testes verdes.

### Contrato congelado

O Permission Designer 2.0 encerra o ciclo mantendo uma única fonte declarativa de autorização:

```text
rbac.roles
rbac.entities[*].roles
rbac.entities[*].transitions
        │
        ├── configuração por capacidades
        ├── configuração de ações de processo
        ├── visão por papel
        ├── visão por funcionalidade
        └── explicação de acesso
```

As visões e explicações são projeções. Nenhuma delas possui política persistida própria.

### Garantias da baseline

- papéis usam linguagem do negócio e IDs internos estáveis;
- capacidades visíveis são traduzidas para o CRUD técnico estável;
- ações de processo continuam referenciando as transições definidas no Workflow Designer;
- configurações antigas permanecem compatíveis;
- autorização continua determinística e fail-closed;
- nenhuma segunda fonte de verdade foi introduzida;
- alterações de configuração refletem imediatamente nas projeções do Designer;
- o runtime RBAC existente continua sendo o responsável por materializar a autorização Django.

### Fora do escopo congelado

Não fazem parte da GEN-067 e não devem ser introduzidos retroativamente nesta baseline:

- vínculo pessoa/usuário -> papel no Designer;
- permissões inventadas para relatórios ou dashboards sem contrato correspondente;
- regras condicionais por registro/objeto;
- nova infraestrutura de autenticação;
- política de autorização paralela ao RBAC declarativo.

Essas capacidades exigem contratos próprios em ciclos futuros.

### Estado

**GEN-067 — Permission Designer 2.0: FROZEN / SAFE BASELINE.**

A evolução posterior deve partir desta baseline sem reabrir as decisões consolidadas do ciclo, salvo correção explícita de regressão.

## Separação de responsabilidades

- Permission Designer expressa **quem pode fazer o quê**.
- contrato RBAC mantém IDs e políticas determinísticas.
- runtime gerado converte papéis em Groups/permissões Django.
- Workflow define **o que pode acontecer**.
- Permission Designer define **quem pode fazer acontecer**.
- Visões `.4`, `.5` e explicação `.6` são projeções do mesmo contrato, nunca fontes independentes de autorização.

## Gate de validação

```text
python manage.py check
python manage.py test sistema.test_rbac
python manage.py test sistema.test_rbac_ui
python manage.py test
```
