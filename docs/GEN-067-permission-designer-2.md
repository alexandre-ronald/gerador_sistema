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

- GEN-067.1 — Papéis orientados ao negócio
- GEN-067.2 — Capacidades em vez de CRUD técnico
- GEN-067.3 — Ações de Workflow
- GEN-067.4 — Visão por papel
- GEN-067.5 — Visão por funcionalidade
- GEN-067.6 — Explicação de acesso
- GEN-067.7 — Testes, regressão e freeze

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

### Objetivo

Permitir que o usuário responda, em linguagem de negócio, **por que uma autorização está permitida ou bloqueada**.

A interface oferece três escolhas:

```text
Papel + Informação + Capacidade/Ação
                ↓
         Explicação de acesso
```

Exemplo de capacidade:

```text
Operador
  ↓
Cadastrar novo
  ↓
Pedido

Permitido: Operador possui a capacidade “Cadastrar novo” sobre Pedido.
```

Exemplo de ação do processo:

```text
Gestor
  ↓
Aprovar
  ↓
Pedido

Permitido: Gestor possui a ação do processo “Aprovar” sobre Pedido.
```

A mesma explicação também representa explicitamente a ausência da autorização, exibindo **Não permitido** quando o papel não consta na política correspondente.

### Regra arquitetural

A explicação nunca é uma nova fonte de autorização. `explainAccess()` consulta diretamente:

```text
rbac.roles
rbac.entities[entidade].roles[papel]
rbac.entities[entidade].transitions[ação]
workflows[entidade]
        ↓
explicação em linguagem de negócio
```

Não existe `accessExplanationState`, política paralela, cache de autorização ou nova persistência.

A explicação é atualizada imediatamente quando uma capacidade ou ação do processo é marcada/desmarcada no Designer.

### Limite desta etapa

A GEN-067.6 explica o contrato por **papel**. Ela não inventa vínculo entre usuários reais e papéis porque esse vínculo não pertence ao contrato atual do Designer. A futura explicação por pessoa poderá compor:

```text
Pessoa -> Papel -> Capacidade/Ação -> Informação
```

quando a identidade/membresia fizer parte de um contrato disponível para essa experiência.

### Preparação arquitetural

Essa projeção prepara uma base reutilizável para:

- diagnóstico de autorização;
- auditoria;
- análise de impacto;
- suporte operacional;
- explicações futuras da camada AI-Native.

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
