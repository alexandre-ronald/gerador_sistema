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

O backend rejeita de forma fail-closed tipo de destinatário desconhecido, papel inexistente, papel com RBAC desativado e propriedade `role` enviada para outro tipo de destinatário.

A interface mostra linguagem de negócio:

```text
Quem deve receber?

  Quem pode visualizar esta informação
  Quem realizou a ação
  Usuários de um papel
      Papel destinatário: Gestor
```

Destinatários baseados em campos do registro exigem metadata semântica própria para declarar que determinado relacionamento representa um usuário. Essa capacidade não deve ser inferida pelo nome do campo.

## Central no sistema gerado — GEN-066.4

Quando existe ao menos uma regra de notificação ativa, o compilador passa a materializar um app interno reservado chamado `djangoforge_notifications`.

A ausência de regras ativas preserva o runtime anterior: o app não é instalado, suas rotas não são emitidas e a central não aparece na navegação.

### Modelo gerado

O runtime possui um modelo `Notification` com os campos:

- `recipient` — usuário destinatário, ligado a `settings.AUTH_USER_MODEL`;
- `title` — título do aviso;
- `message` — mensagem;
- `url` — destino interno opcional para abrir a informação relacionada;
- `read_at` — instante em que a notificação foi lida;
- `created_at` — instante de criação.

Foi escolhido `read_at` em vez de um booleano `is_read` para preservar informação temporal e permitir evolução posterior sem alterar o contrato básico.

O app é acompanhado de migration inicial explícita. O sistema gerado não depende de `makemigrations` manual para materializar a tabela da central.

### Segurança da central

Toda leitura é escopada ao usuário autenticado:

```text
Notification.objects.filter(recipient=request.user)
```

Marcar uma notificação como lida exige POST e busca simultaneamente por `pk` e `recipient=request.user`. Assim, conhecer o ID de uma notificação de outro usuário não concede acesso a ela.

As mutações suportadas nesta fase são:

- marcar uma notificação como lida;
- marcar todas as notificações do próprio usuário como lidas.

### Navegação e contador

A central é publicada em:

```text
/notifications/
```

A navegação global recebe a área `Comunicação` com o item `Notificações`. Quando houver itens não lidos, o label inclui a quantidade, por exemplo:

```text
Comunicação
  Notificações (3)
```

A contagem é sempre calculada para o usuário autenticado. Falha de acesso à tabela durante bootstrap/migration não derruba a navegação; nesse caso o contador degrada para zero.

### Interface

A central permite:

- visualizar todas as notificações;
- filtrar apenas não lidas;
- distinguir visualmente itens novos;
- marcar uma notificação como lida;
- marcar todas como lidas;
- abrir o destino relacionado quando `url` estiver preenchida.

A listagem inicial é deliberadamente limitada no runtime desta fase. Paginação e políticas de retenção podem ser evoluídas sem alterar o contrato de emissão.

## Limites da GEN-066.4

A GEN-066.4 cria a infraestrutura funcional de armazenamento e leitura, mas ainda não produz notificações a partir das regras do Designer.

Portanto ainda estão fora desta etapa:

- interceptar Create/Update/Delete dos CRUDs;
- interceptar transições de Workflow;
- resolver `actor`, `role` e `users_with_view_permission` durante um acontecimento;
- criar objetos `Notification` automaticamente;
- deduplicação de destinatários durante o disparo;
- e-mail, SMS, push, WebSocket, filas, Celery ou brokers.

A integração efetiva das regras com CRUD/Workflow é responsabilidade exclusiva da GEN-066.5.

## Separação de responsabilidades

- Workflow define **o que pode acontecer**.
- RBAC define **quem pode executar e visualizar ações**.
- Notification Designer define **sobre quais acontecimentos avisar e quem deve receber**.
- GEN-066.4 fornece **onde a notificação é armazenada, consultada e marcada como lida**.
- GEN-066.5 fará **quando criar a notificação, como resolver seus destinatários e o freeze**.

Até a GEN-066.4 não há envio de e-mail, fila, Celery, WebSocket nem execução de código configurável.
