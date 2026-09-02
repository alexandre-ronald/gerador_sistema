# GEN-057 — Deployment Center

## Objetivo

Transformar o ciclo lógico de releases e ambientes do DjangoForge em um contrato seguro e auditável de implantação, preparando a execução real de deploy sem acoplar o DjangoForge a um provedor específico.

A GEN-057 parte do baseline validado da GEN-056 (`c25ae51279cd5bf74325f0cfdb065d6433930516`) e conecta formalmente:

`Release → Ambiente → Plano de Deploy → Execução → Verificação pelo Runtime Agent`

## Princípios

1. **Deploy explícito** — nenhuma implantação ocorre por salvar configuração, gerar sistema ou promover release.
2. **Somente RELEASED** — apenas releases publicadas podem originar deploy.
3. **Ambiente obrigatório** — todo deploy pertence a um `Ambiente` existente do mesmo Sistema.
4. **Fail closed** — configuração desconhecida, incompleta ou inconsistente bloqueia a execução.
5. **Auditoria imutável** — cada tentativa gera histórico próprio; tentativas anteriores nunca são sobrescritas.
6. **Sem secrets em texto puro** — credenciais são referências a variáveis de ambiente.
7. **Contrato fechado** — tipos de executor, estratégias e estados são enumerados.
8. **Separação entre plano e execução** — criar/validar plano não executa comandos.
9. **Runtime Agent é a fonte de verificação pós-deploy** — sucesso do comando não significa automaticamente ambiente saudável.
10. **Compatibilidade** — sistemas sem configuração de deployment preservam o comportamento da GEN-056.

## Escopo da GEN-057

### Incluído

- Deployment Center por Sistema;
- configuração declarativa por ambiente;
- criação de plano de deploy para uma release publicada;
- validação do plano antes da execução;
- estados formais de deployment;
- histórico de tentativas;
- executor local controlado para desenvolvimento/teste;
- executor SSH como contrato configurável para ambientes remotos;
- estratégia Docker Compose;
- diretório remoto/local de aplicação;
- referência de variáveis de ambiente para credenciais;
- comandos fechados e gerados pelo DjangoForge, sem shell arbitrário informado pelo usuário;
- etapas `prepare`, `deploy`, `verify`;
- verificação pós-deploy pelo Runtime Agent existente;
- comparação entre release solicitada e release observada;
- UI owner-only;
- testes de contrato, segurança, estados e regressão.

### Fora do escopo

- Kubernetes;
- Docker Swarm;
- Terraform/Ansible;
- AWS/Azure/GCP específicos;
- pipelines GitHub Actions/GitLab/Jenkins;
- deploy blue/green;
- canary;
- autoscaling;
- gestão de DNS/TLS;
- provisionamento de servidor;
- criação de banco de dados remoto;
- secret vault;
- terminal remoto arbitrário;
- comandos shell livres;
- rollback automático;
- logs centralizados de aplicação (GEN-058);
- backup automático (GEN-059).

## Persistência declarativa

A configuração de deployment pertence ao draft do sistema:

```json
{
  "deployment": {
    "enabled": true,
    "environments": {
      "DEVELOPMENT": {
        "executor": "local",
        "strategy": "docker_compose",
        "working_directory": "C:/apps/aprovaflow",
        "compose_file": "docker-compose.yml"
      },
      "PRODUCTION": {
        "executor": "ssh",
        "strategy": "docker_compose",
        "host": "app.exemplo.gov.br",
        "port": 22,
        "username_env_var": "DEPLOY_PROD_USERNAME",
        "private_key_env_var": "DEPLOY_PROD_PRIVATE_KEY",
        "working_directory": "/opt/aprovaflow",
        "compose_file": "docker-compose.yml"
      }
    }
  }
}
```

Nenhum valor de senha, token ou chave privada pode ser persistido em `estrutura_json`.

## Contrato de configuração

### Global

- `enabled`: boolean.
- `environments`: objeto indexado exclusivamente por `DEVELOPMENT`, `TEST`, `STAGING`, `PRODUCTION`.

### Executor

Valores permitidos:

- `local`
- `ssh`

### Estratégia

GEN-057 aceita inicialmente apenas:

- `docker_compose`

### Configuração comum

- `executor`
- `strategy`
- `working_directory`
- `compose_file`, default `docker-compose.yml`

`working_directory` deve ser absoluto e não pode conter caracteres de controle.

`compose_file` deve ser nome/caminho relativo seguro, sem `..`, sem caminho absoluto e sem caracteres de controle.

### Executor local

Não possui credenciais.

Seu uso deve ser restrito inicialmente a `DEVELOPMENT` e `TEST`. `STAGING` e `PRODUCTION` devem usar executor remoto.

### Executor SSH

Campos:

- `host`
- `port`, default 22, intervalo 1..65535
- `username_env_var`
- `private_key_env_var`

Opcionalmente, em evolução compatível:

- `known_hosts_env_var`

Os campos de credencial contêm somente nomes seguros de variáveis de ambiente (`[A-Z][A-Z0-9_]*`).

## Plano de Deploy

Um plano é uma representação persistida e auditável da intenção de implantação.

Campos conceituais:

- sistema;
- ambiente;
- release;
- executor;
- estratégia;
- status;
- criado_por;
- criado_em;
- iniciado_em;
- finalizado_em;
- release_observada;
- erro seguro;
- resumo das etapas.

O plano copia a configuração necessária no momento da criação para impedir que uma edição posterior altere retroativamente o significado de uma tentativa já criada.

## Estados

Estados permitidos:

- `PLANNED`
- `VALIDATING`
- `READY`
- `RUNNING`
- `VERIFYING`
- `SUCCEEDED`
- `FAILED`
- `CANCELLED`

Fluxo nominal:

`PLANNED → VALIDATING → READY → RUNNING → VERIFYING → SUCCEEDED`

Falhas em validação:

`PLANNED → VALIDATING → FAILED`

Falhas de execução/verificação:

`READY → RUNNING → FAILED`

ou

`RUNNING → VERIFYING → FAILED`

Cancelamento só é permitido antes de `RUNNING`.

Estados finais (`SUCCEEDED`, `FAILED`, `CANCELLED`) são imutáveis.

## Etapas da estratégia Docker Compose

A GEN-057 não aceita texto de shell arbitrário. O executor monta internamente uma sequência fechada.

### prepare

- verificar existência/acesso ao diretório;
- verificar disponibilidade do Docker;
- verificar disponibilidade de Docker Compose;
- verificar existência do compose file;
- validar configuração do Compose.

### deploy

Sequência conceitual:

1. materializar/obter o artefato da release;
2. posicionar artefato no diretório configurado;
3. executar `docker compose pull` quando aplicável;
4. executar `docker compose build` quando aplicável;
5. executar `docker compose up -d`;

A definição exata de artefato e política pull/build será fechada na fase de runtime sem permitir comandos livres.

### verify

- consultar Runtime Agent;
- exigir Agent online;
- comparar `DJANGOFORGE_RELEASE` observado com a release solicitada;
- considerar migrations pendentes e estado reportado;
- persistir resultado.

## Relação com Environment Manager

`Ambiente.release_atual` representa a release desejada/promovida logicamente.

Deployment Center não deve silenciosamente mudar a release desejada para mascarar drift.

Para executar deploy:

- a release deve ser `RELEASED`;
- deve pertencer ao mesmo Sistema;
- deve corresponder à release atualmente promovida para o ambiente, salvo uma futura operação explícita de rollback.

## Relação com Runtime Agent / Health

Após a execução, o Deployment Center reutiliza o contrato da GEN-045.

Um deploy só chega a `SUCCEEDED` se a verificação confirmar, no mínimo:

- Agent online;
- contrato válido;
- release observada igual à release do plano;
- status operacional aceitável;
- nenhuma condição definida como bloqueante.

Falha de verificação não apaga o fato de que os comandos de implantação foram executados. O plano fica `FAILED` com a etapa `verify` identificada.

## Segurança

- todas as views são owner-only;
- POST obrigatório para criar, validar, executar ou cancelar;
- CSRF obrigatório;
- credenciais somente por env vars;
- nunca registrar conteúdo de chave/token/senha;
- mensagens de erro devem ser sanitizadas;
- nenhum parâmetro do usuário vira comando shell livre;
- subprocess deve usar lista de argumentos e `shell=False` no executor local;
- SSH deve executar somente comandos construídos pelo contrato fechado;
- timeout obrigatório por etapa;
- host, caminhos e compose file validados antes da execução;
- Production exige confirmação explícita na UI antes de iniciar execução.

## UI

Rota principal proposta:

`/sistemas/<id>/deployments/`

A tela deve mostrar:

- resumo dos quatro ambientes;
- release desejada;
- release observada;
- saúde atual;
- configuração de deployment;
- último deployment;
- botão `Criar plano`;
- botão `Validar plano`;
- botão `Executar deploy` somente quando `READY`;
- histórico de deployments;
- etapas e erros seguros.

A configuração de executor deve ficar separada da ação de executar deploy.

## Fases

### GEN-057.1 — Contract & Architecture

- contrato declarativo;
- normalizador/validador;
- estados e transições;
- testes de contrato;
- nenhuma execução de deploy.

### GEN-057.2 — UI / Backend / Persistence

- modelos de plano/histórico;
- migration;
- views owner-only;
- configuração visual;
- criação/validação/cancelamento de planos;
- workspace;
- nenhuma execução remota ainda.

### GEN-057.3 — Deployment Runtime

- executor local controlado;
- executor SSH;
- estratégia Docker Compose;
- timeouts;
- captura/sanitização de resultado;
- verificação via Runtime Agent;
- estados RUNNING/VERIFYING/SUCCEEDED/FAILED.

### GEN-057.4 — Regression & Manual Validation

- suíte completa;
- teste local Docker Compose controlado;
- teste de falha;
- teste de drift pós-deploy;
- validação manual;
- promoção para master.

## Critérios de aceite da GEN-057.1

1. baseline é exatamente a master validada da GEN-056;
2. configuração ausente normaliza para deployment desativado;
3. tipos de ambiente, executor e estratégia são fechados;
4. Production não aceita executor local;
5. nomes de env vars são validados e nenhum secret é aceito;
6. working directory e compose file são validados;
7. estados e transições de deployment são fechados;
8. configuração inválida falha de forma estruturada;
9. modo tolerante permite abrir drafts antigos sem quebrar a UI;
10. nenhuma função da GEN-057.1 executa subprocess, SSH, Docker, migration ou rede;
11. testes anteriores continuam passando.
