# GEN-045 — Runtime Agent

## Objetivo

Criar o primeiro contrato de comunicação entre o DjangoForge e os sistemas gerados, permitindo que cada ambiente exponha seu estado real sem executar deploy remoto ou ações destrutivas.

## Contrato do Agent

Todo sistema gerado passa a expor:

`GET /__djangoforge__/status/`

Resposta JSON mínima:

- `contract`: versão do contrato (`1.0`)
- `status`: `ok` ou `degraded`
- `system`: nome do sistema
- `environment`: valor de `DJANGOFORGE_ENVIRONMENT`
- `release`: valor de `DJANGOFORGE_RELEASE`
- `database.vendor`
- `migrations.pending`
- `uptime_seconds`
- `timestamp`

O endpoint é somente leitura. Não aplica migrations, não altera banco, não executa comandos remotos e não contém credenciais.

## DjangoForge

O Environment Manager passa a possuir uma ação explícita de verificação do Runtime Agent. A consulta usa a URL base cadastrada no ambiente e persiste apenas o último snapshot observado.

O snapshot registra:

- conectividade
- contrato recebido
- status reportado
- release reportada
- ambiente reportado
- banco reportado
- migrations pendentes
- uptime
- payload bruto para diagnóstico
- erro de comunicação, quando houver
- data/hora da verificação

## Segurança

- somente o proprietário do sistema pode disparar a consulta;
- somente URLs `http` e `https` são aceitas;
- timeout curto;
- nenhum segredo é enviado ao Agent nesta primeira versão;
- nenhuma operação de deploy é executada;
- nenhuma migration remota é aplicada.

## Fora do escopo

- heartbeat automático;
- autenticação/token entre Forge e Agent;
- deploy remoto;
- rollback remoto;
- coleta contínua de métricas;
- logs remotos;
- alertas.

Essas capacidades serão evoluídas na GEN-046 e gerações posteriores.

## Critérios de aceite

1. sistema gerado contém o endpoint do Runtime Agent;
2. endpoint retorna contrato estável e somente leitura;
3. migrations pendentes são detectadas sem aplicá-las;
4. DjangoForge consulta ambientes configurados;
5. último snapshot é persistido;
6. falha de conexão é registrada sem quebrar o Environment Manager;
7. release desejada e release observada ficam visualmente comparáveis;
8. testes anteriores continuam passando.