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

Somente são oferecidas como eventos notificáveis transições que pertencem a workflow ativo, estão habilitadas, possuem origens válidas e possuem destino válido.

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

Representa os usuários autorizados a visualizar a entidade.

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

Destinatários baseados em campos do registro exigem metadata semântica própria para declarar que determinado relacionamento representa um usuário. Essa capacidade não deve ser inferida pelo nome do campo.

## Central no sistema gerado — GEN-066.4

Quando existe ao menos uma regra de notificação ativa, o compilador materializa um app interno reservado chamado `djangoforge_notifications`.

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

O app é acompanhado de migration inicial explícita.

### Segurança da central

Toda leitura é escopada ao usuário autenticado. Marcar uma notificação como lida exige POST e busca simultaneamente por `pk` e `recipient=request.user`.

### Navegação e contador

A central é publicada em `/notifications/`. A navegação global recebe a área `Comunicação` com o item `Notificações`, incluindo a quantidade não lida quando maior que zero.

## Integração de runtime — GEN-066.5

A GEN-066.5 fecha o circuito entre acontecimentos do sistema e a Central de Notificações.

Fluxo materializado:

```text
ação de negócio
    ↓
Create / Update / Delete / WorkflowTransitionHistory
    ↓
signal do runtime gerado
    ↓
regra declarada no Notification Designer
    ↓
resolução dos destinatários
    ↓
Notification
    ↓
Central de notificações
```

### Captura dos eventos

Os CRUDs não recebem código específico de notificação. O app interno conecta `post_save` e `post_delete` aos modelos que possuem regras ativas.

A semântica é:

- `post_save(created=True)` → `created`;
- `post_save(created=False)` → `updated`;
- `post_delete` → `deleted`.

A escolha por signals mantém o recurso transversal e também cobre alterações realizadas por outras superfícies do runtime, como API e administração, desde que usem o ORM Django.

### Ator autenticado

O app interno instala `NotificationActorMiddleware` imediatamente após `AuthenticationMiddleware`. O middleware mantém o usuário da requisição em `ContextVar`, permitindo que os signals resolvam `audience = "actor"` sem acoplar cada CRUD à infraestrutura de notificação.

O contexto é sempre restaurado em `finally`, evitando vazamento do usuário entre requisições ou contextos concorrentes.

Para eventos de Workflow, o usuário persistido em `WorkflowTransitionHistory.user` é a fonte preferencial do ator.

### Eventos de Workflow

O runtime observa a criação de `WorkflowTransitionHistory` e usa simultaneamente:

- `app_label`;
- `model_name`;
- `transition_id`.

Assim uma regra `workflow_transition` só dispara quando o ID da transição executada coincide exatamente com o ID persistido na regra.

### Resolução dos destinatários

`actor` resolve exclusivamente o usuário autenticado que provocou a ação, quando ativo.

`role` consulta o contrato RBAC gerado, resolve o ID estável do papel para seu Django Group e seleciona usuários ativos pertencentes ao grupo. Se RBAC estiver desativado ou o papel estiver stale, a resolução retorna vazio.

`users_with_view_permission` usa duas estratégias:

- com RBAC ativo, considera superusuários e usuários ativos em papéis que possuam `list` ou `view` para a entidade;
- sem RBAC ativo, considera superusuários e usuários ativos que possuam a permissão Django `view_<model>` direta ou por grupo.

A resolução é fail-closed para audiência desconhecida ou metadata ausente.

### Deduplicação

A deduplicação ocorre por regra e usuário. Um usuário alcançado por mais de um grupo/permissão recebe somente uma instância daquela regra.

Regras distintas continuam independentes. Portanto, duas regras diferentes para o mesmo evento podem produzir duas notificações diferentes para o mesmo usuário, preservando a intenção declarada pelo usuário no Designer.

### Destino interno

Quando a entidade possui página de detalhe gerada, eventos de criação, atualização e Workflow apontam para essa página. Caso contrário é utilizada a listagem quando disponível.

Eventos de exclusão apontam para a listagem, pois o objeto já não existe.

### Fail-closed na geração

Além da validação do Designer, o template tag de geração ignora regras estruturalmente inválidas. Não entram no runtime regras com evento ou audiência desconhecidos, transição ausente para evento de Workflow, transição indevida em evento CRUD, papel ausente para audiência `role`, ou campos essenciais vazios.

Não há `eval`, `exec` ou código configurável pelo usuário.

## Limites mantidos após GEN-066.5

A GEN-066 continua deliberadamente sem:

- e-mail;
- SMS;
- push externo;
- WebSocket;
- Celery;
- brokers ou filas;
- endereço de destinatário digitado livremente;
- destinatário inferido pelo nome de um campo do modelo.

A primeira versão é uma central interna persistida no mesmo banco do sistema gerado.

## Critério de freeze

A GEN-066 pode ser congelada quando passarem:

```text
python manage.py check
python manage.py test sistema.test_generated_notifications
python manage.py test sistema.test_notification_designer_ui
python manage.py test
```

O freeze confirma o seguinte contrato:

- Designer e persistência estáveis;
- eventos CRUD e Workflow estáveis;
- destinatários `users_with_view_permission`, `actor` e `role` estáveis;
- central gerada e protegida por usuário;
- captura transversal por signals;
- ator propagado por middleware/contexto seguro;
- deduplicação por regra/destinatário;
- ausência de infraestrutura externa de mensageria;
- regressão global verde.

## Separação de responsabilidades

- Workflow define **o que pode acontecer**.
- RBAC define **quem pode executar e visualizar ações**.
- Notification Designer define **sobre quais acontecimentos avisar e quem deve receber**.
- Runtime de notificações detecta **quando o acontecimento realmente ocorreu** e resolve seus destinatários.
- Central de notificações fornece **armazenamento, leitura e estado de lida**.
