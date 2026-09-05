# GEN-067 — Permission Designer 2.0

## Objetivo

Permitir que o usuário defina **quem pode fazer o quê** usando a linguagem do negócio, sem precisar compreender RBAC, Django Groups, codenames de permissões ou detalhes de implementação.

Princípio de produto:

> O usuário descreve responsabilidades e ações permitidas. O DjangoForge materializa autorização Django/RBAC no sistema gerado.

## Filosofia

A GEN-067 inaugura formalmente a experiência orientada à intenção do usuário:

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

### Experiência

O Designer deixa de pedir ao usuário:

- ID técnico do papel;
- Django Group;
- conhecimento do termo RBAC.

O usuário informa:

- nome do papel;
- descrição da responsabilidade.

Exemplo:

```text
Gestor de Contratos
Responsável por acompanhar e aprovar contratos.
```

### Contrato persistido

O runtime preserva IDs estáveis e Django Groups internamente:

```json
{
  "id": "gestor_contratos",
  "label": "Gestor de Contratos",
  "description": "Responsável por acompanhar e aprovar contratos.",
  "group": "Gestor de Contratos",
  "order": 0
}
```

`description` é metadata de negócio e não altera a resolução de autorização.

### Retrocompatibilidade

Configurações antigas que já possuem `group` continuam preservando seu valor.

Quando um novo contrato não fornece `group`, o normalizador deriva o grupo interno a partir de `label`. Assim a interface não precisa expor detalhes Django, mas o runtime existente continua recebendo o contrato esperado.

IDs continuam estáveis. Alterar o nome visual de um papel não deve reescrever referências existentes em políticas de entidade ou permissões de Workflow.

### Separação de responsabilidades

- Permission Designer expressa **quem pode fazer o quê**.
- contrato RBAC mantém IDs e políticas determinísticas.
- runtime gerado converte os papéis em Groups/permissões Django.
- Workflow continua definindo se uma transição é estruturalmente possível; Permission Designer apenas define quem pode executá-la.

## Critério da GEN-067.1

A etapa pode ser fechada quando passarem:

```text
python manage.py check
python manage.py test sistema.test_rbac
python manage.py test sistema.test_rbac_ui
python manage.py test
```

E quando estiver confirmado que:

- contratos RBAC antigos continuam válidos;
- grupos antigos continuam preservados;
- novos papéis podem ser salvos sem `group` explícito;
- descrição do papel é persistida;
- interface não expõe `RBAC ativo`, `Django Group`, `Matriz de permissões CRUD` ou `Permissões de Workflow`;
- IDs técnicos permanecem internos e estáveis;
- regressão global permanece verde.
