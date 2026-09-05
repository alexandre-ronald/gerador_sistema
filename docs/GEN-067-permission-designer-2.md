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

O usuário informa nome e descrição da responsabilidade. IDs técnicos e Django Groups permanecem internos.

```json
{
  "id": "gestor_contratos",
  "label": "Gestor de Contratos",
  "description": "Responsável por acompanhar e aprovar contratos.",
  "group": "Gestor de Contratos",
  "order": 0
}
```

Configurações antigas com `group` explícito preservam esse valor. Em novos papéis, o grupo interno pode ser derivado de `label`. IDs permanecem estáveis.

## GEN-067.2 — Capacidades em vez de CRUD técnico

A interface traduz o contrato CRUD estável para capacidades orientadas ao negócio:

```text
Consultar registros -> list
Ver detalhes        -> view
Cadastrar novo      -> create
Alterar registros   -> update
Excluir registros   -> delete
```

Persistência continua usando os mesmos IDs técnicos, garantindo retrocompatibilidade.

Organização visual:

```text
Informação
  -> Papel
      -> Capacidades
```

## GEN-067.3 — Ações de Workflow

O Workflow Designer continua sendo a fonte das ações possíveis do processo. O Permission Designer apenas responde **quem pode executá-las**.

Experiência:

```text
Pedido
Ações disponíveis neste processo

Gestor
[x] Aprovar
[ ] Cancelar
```

O contrato permanece:

```json
{
  "transitions": {
    "aprovar": ["gestor"]
  }
}
```

Nenhuma transição é duplicada ou redefinida no Permission Designer.

## GEN-067.4 — Visão por papel

### Objetivo

Permitir que o usuário escolha um papel e compreenda rapidamente **tudo o que esse papel pode fazer na aplicação**.

Exemplo:

```text
Gestor de Contratos
Responsável por acompanhar e aprovar contratos.

Contrato
  ✓ Consultar registros
  ✓ Ver detalhes
  ✓ Alterar registros

Ações do processo
  ✓ Aprovar
  ✓ Devolver para correção
```

### Regra arquitetural

A visão por papel é **derivada do mesmo contrato RBAC**. Ela não possui persistência própria e não cria uma segunda fonte de verdade.

```text
rbac.roles
rbac.entities[*].roles
rbac.entities[*].transitions
        ↓
Visão por papel
```

Alterações nas capacidades ou ações de processo atualizam imediatamente o resumo do papel selecionado.

`selectedRoleId` é apenas estado transitório de interface; não faz parte do contrato persistido.

### Contadores

A visão exibe, para o papel selecionado:

- quantidade de capacidades sobre informações;
- quantidade de ações de processo;
- total de permissões resultantes.

Esses valores são calculados a partir do contrato atual e não são armazenados.

### Critério da GEN-067.4

A etapa pode ser fechada quando:

- todos os papéis puderem ser selecionados na visão consolidada;
- nome e descrição do papel forem apresentados;
- capacidades autorizadas forem agrupadas por informação;
- ações de Workflow autorizadas forem agrupadas por processo;
- mudanças realizadas nas seções de configuração refletirem imediatamente no resumo;
- nenhum novo contrato ou estado persistente for criado para a visão;
- configurações antigas continuarem compatíveis;
- regressão global permanecer verde.

## Separação de responsabilidades

- Permission Designer expressa **quem pode fazer o quê**.
- contrato RBAC mantém IDs e políticas determinísticas.
- runtime gerado converte os papéis em Groups/permissões Django.
- Workflow define **o que pode acontecer**.
- Permission Designer define **quem pode fazer acontecer**.
- Visões `.4` e `.5` são projeções do mesmo contrato, nunca fontes independentes de autorização.

## Gate de validação

```text
python manage.py check
python manage.py test sistema.test_rbac
python manage.py test sistema.test_rbac_ui
python manage.py test
```
