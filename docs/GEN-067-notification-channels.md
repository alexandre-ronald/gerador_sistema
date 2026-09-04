# GEN-067 — Canais de Notificação

## Objetivo

Evoluir a GEN-066 para permitir que uma regra de notificação escolha **onde** o aviso deve ser entregue, preservando a Central interna como comportamento estável e padrão.

Princípio de experiência:

> O usuário escolhe o acontecimento, os destinatários e os canais. O Gerador materializa a entrega sem expor infraestrutura de mensageria.

## Base

A GEN-067 nasce da baseline congelada `gen-066-regression-safe-baseline`.

A GEN-066 permanece responsável por:

- eventos CRUD e Workflow;
- destinatários;
- Central interna;
- criação persistida de `Notification`.

A GEN-067 não altera a semântica desses contratos.

## Roadmap

- GEN-067.1 — Contrato de canais + compatibilidade retroativa
- GEN-067.2 — Designer de canais
- GEN-067.3 — Canal e-mail no runtime gerado
- GEN-067.4 — Registro de tentativas/falhas de entrega
- GEN-067.5 — Integração, regressão e freeze

## GEN-067.1 — Contrato

Uma regra pode declarar `channels`:

```json
{
  "id": "contrato_criado",
  "enabled": true,
  "event": "created",
  "title": "Novo contrato",
  "message": "Um novo contrato foi cadastrado.",
  "audience": "users_with_view_permission",
  "channels": ["in_app"]
}
```

### Canais iniciais

- `in_app` — Central de notificações já existente.

O canal `email` será introduzido somente na GEN-067.3, após o Designer possuir contrato estável.

### Compatibilidade retroativa

Regras da GEN-066 que não possuem `channels` são interpretadas como:

```json
{
  "channels": ["in_app"]
}
```

Assim sistemas existentes continuam produzindo exatamente a mesma Central interna sem migração do draft.

### Normalização

A normalização deve:

- aceitar somente canais conhecidos;
- remover duplicidades preservando a ordem;
- rejeitar lista vazia;
- assumir `["in_app"]` quando a chave estiver ausente;
- rejeitar tipos diferentes de lista;
- permanecer fail-closed para valores desconhecidos.

### Separação de responsabilidades

- Notification Designer define **quando**, **quem** e **por quais canais** avisar.
- O runtime da GEN-066 continua detectando o acontecimento e resolvendo destinatários.
- Cada canal é responsável apenas por sua forma de entrega.

## Fora do escopo da GEN-067.1

- envio real de e-mail;
- SMTP;
- Celery;
- brokers/filas;
- SMS;
- push móvel;
- WebSocket;
- templates HTML de e-mail;
- retries.

## Critério de conclusão da GEN-067.1

- regra antiga sem `channels` continua válida e equivale a `in_app`;
- `channels=["in_app"]` persiste e é gerado corretamente;
- canal desconhecido é rejeitado;
- lista vazia é rejeitada;
- nenhuma regressão na GEN-066;
- suíte global verde.
