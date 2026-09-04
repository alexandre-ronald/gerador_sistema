# GEN-066 — Notification Designer

## Objetivo

Permitir que o usuário declare avisos de negócio sem configurar infraestrutura de mensageria.

Princípio de experiência:

> O usuário informa quando quer avisar e quem deve receber. O Gerador materializa a implementação necessária no sistema Django gerado.

## Roadmap

- GEN-066.1 — Designer + persistência
- GEN-066.2 — Eventos de Workflow
- GEN-066.3 — Destinatários
- GEN-066.4 — Central de notificações no sistema gerado
- GEN-066.5 — Integração CRUD/Workflow + freeze

## Contrato persistido

As notificações vivem no draft `VersaoGeracao.numero=0`, na chave `notifications`, preservando as demais chaves de `estrutura_json`.

### Evento CRUD

```json
{
  "id": "contrato_criado",
  "enabled": true,
  "event": "created",
  "title": "Novo contrato",
  "message": "Um novo contrato foi cadastrado.",
  "audience": "users_with_view_permission"
}
```

Eventos CRUD suportados:

- `created`
- `updated`
- `deleted`

### Evento de Workflow — GEN-066.2

```json
{
  "id": "contrato_aprovado",
  "enabled": true,
  "event": "workflow_transition",
  "transition": "aprovar",
  "title": "Contrato aprovado",
  "message": "O contrato foi aprovado.",
  "audience": "users_with_view_permission"
}
```

A notificação referencia o ID estável da transição do Workflow, e não o label nem o valor visual do estado.

## Semântica GEN-066.2

O Notification Designer lê a configuração persistida em `workflows` para a mesma entidade.

Somente são oferecidas como eventos notificáveis transições que:

- pertencem a workflow ativo;
- estão habilitadas;
- possuem origens válidas;
- possuem destino válido.

A interface apresenta linguagem de negócio, por exemplo:

```text
Quando avisar?

Cadastro
  Quando um registro for criado
  Quando um registro for atualizado
  Quando um registro for excluído

Mudança de situação
  Quando mudar de Rascunho para Em análise
  Quando mudar de Em análise para Aprovado
```

O backend continua fail-closed. Ao salvar uma regra `workflow_transition`, rejeita workflow inexistente/desativado, transição inexistente/desabilitada e uso de `transition` fora de evento de workflow.

Configuração antiga ou stale pode ser exibida pelo Designer como indisponível, mas não pode ser salva novamente sem correção.

## Destinatários — GEN-066.3

A primeira versão de destinatários usa um contrato simples, determinístico e resolvível no runtime gerado.

### Quem pode visualizar esta informação

```json
{
  "audience": "users_with_view_permission"
}
```

Representa os usuários autorizados a visualizar a entidade. A resolução concreta será materializada no runtime gerado usando as permissões disponíveis.

### Quem realizou a ação

```json
{
  "audience": "actor"
}
```

Representa o usuário autenticado que provocou o acontecimento: criação, alteração, exclusão ou execução de transição.

### Usuários de um papel RBAC

```json
{
  "audience": "role",
  "role": "gestor"
}
```

O campo `role` referencia o ID estável de um papel já definido em `estrutura_json["rbac"]["roles"]`. O Notification Designer não duplica nomes de Django Groups nem cria uma segunda definição de papéis.

Para usar `audience = "role"`:

- RBAC deve estar ativo;
- o papel precisa existir;
- o papel precisa possuir ID válido no contrato RBAC.

O backend rejeita de forma fail-closed:

- tipo de destinatário desconhecido;
- papel inexistente;
- papel usado com RBAC desativado;
- propriedade `role` enviada para outro tipo de destinatário.

A interface mostra linguagem de negócio:

```text
Quem deve receber?

  Quem pode visualizar esta informação
  Quem realizou a ação
  Usuários de um papel
      Papel destinatário: Gestor
```

## Limites da GEN-066.3

Não fazem parte desta etapa:

- destinatário por campo do registro, como `responsavel` ou `solicitante`;
- `created_by` implícito quando o modelo não declara essa semântica;
- endereço de e-mail informado manualmente;
- grupos digitados livremente;
- canais de entrega;
- templates de e-mail;
- filas, Celery ou brokers;
- WebSocket;
- entrega efetiva da notificação.

Destinatários baseados em campos do registro exigem metadata semântica própria para declarar que determinado relacionamento representa um usuário. Essa capacidade não deve ser inferida pelo nome do campo.

## Separação de responsabilidades

- Workflow define **o que pode acontecer**.
- RBAC define **quem pode executar e visualizar ações**.
- Notification Designer define **sobre quais acontecimentos avisar e quem deve receber**.
- GEN-066.4 materializará a central de notificações no sistema gerado.
- GEN-066.5 fará a integração efetiva com CRUD/Workflow e o freeze.

A GEN-066.3 continua sem enviar e-mail, sem criar fila, sem Celery, sem WebSocket e sem executar código configurável.
