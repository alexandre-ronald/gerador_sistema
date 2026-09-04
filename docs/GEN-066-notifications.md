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

Eventos CRUD suportados nesta fase:

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

O backend continua fail-closed. Ao salvar uma regra `workflow_transition`, rejeita:

- workflow inexistente ou desativado;
- transição inexistente;
- transição desabilitada;
- uso de `transition` em evento que não seja de workflow.

Configuração antiga ou stale pode ser exibida pelo Designer como indisponível, mas não pode ser salva novamente sem correção.

## Separação de responsabilidades

- Workflow define **o que pode acontecer**.
- Notification Designer define **sobre quais acontecimentos avisar**.
- Destinatários serão tratados na GEN-066.3.
- Entrega e central de notificações no runtime gerado serão tratadas nas GEN-066.4 e GEN-066.5.

A GEN-066.2 não envia e-mail, não cria fila, não usa Celery, não cria WebSocket e não executa código configurável.
