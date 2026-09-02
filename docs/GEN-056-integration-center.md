# GEN-056 — Integration Center

Status: Draft 0.1
Baseline: GEN-055 (`049d8da52008277027cab36a540af50af0bdd82b`)

## 1. Objetivo

Adicionar ao DjangoForge um centro declarativo para configurar integrações HTTP de saída dos sistemas gerados, sem exigir código Python manual e sem acoplar o runtime gerado ao próprio DjangoForge.

O Integration Center complementa o API Designer:

- API Designer: expõe dados e operações do sistema para consumidores externos.
- Integration Center: permite que o sistema gerado consuma serviços HTTP externos.

## 2. Princípios

1. Configuração declarativa; nenhum Python/JS arbitrário.
2. Fail closed para integração, operação, método, autenticação ou template inválido.
3. Sem configuração de integrações => comportamento idêntico à GEN-055.
4. Runtime gerado independente do DjangoForge.
5. Segredos nunca são persistidos em claro no contrato de geração; o contrato referencia variáveis de ambiente.
6. Timeouts obrigatórios e limitados.
7. Métodos HTTP e autenticação pertencem a conjuntos fechados.
8. O sistema gerado deve distinguir falha HTTP, timeout, resposta inválida e erro de configuração.
9. Identificadores e nomes de integração devem ser determinísticos e seguros.
10. A primeira versão é intencionalmente pequena: cliente HTTP declarativo, não uma plataforma iPaaS.

## 3. Escopo GEN-056

### Incluído

- integrações HTTP/HTTPS de saída;
- cadastro visual de integrações;
- base URL;
- endpoints/operações por integração;
- GET, POST, PUT, PATCH e DELETE;
- autenticação `none`, `basic`, `bearer` e `api_key`;
- credenciais referenciadas por variáveis de ambiente;
- headers estáticos não secretos;
- query parameters declarativos;
- body JSON declarativo;
- timeout;
- teste de contrato/configuração dentro do DjangoForge sem executar chamadas externas;
- geração de cliente HTTP independente no sistema gerado;
- exceções de runtime padronizadas;
- helper para leitura de resposta JSON;
- workspace visual;
- testes de compatibilidade com GEN-055.

### Não incluído

- OAuth2/OIDC flows;
- refresh token;
- SOAP;
- GraphQL;
- gRPC;
- filas/mensageria;
- Kafka/RabbitMQ;
- webhooks recebidos;
- scheduler;
- retries avançados/circuit breaker;
- transformação arbitrária de payload;
- scripts Python/JavaScript;
- ETL;
- sincronização bidirecional automática;
- armazenamento de secrets no DjangoForge;
- marketplace de conectores.

Esses itens ficam para evoluções posteriores do Integration Center ou módulos específicos.

## 4. Persistência

Persistência no draft (`VersaoGeracao.numero=0`):

```json
{
  "integrations": {
    "enabled": true,
    "items": [
      {
        "id": "erp_corporativo",
        "label": "ERP Corporativo",
        "base_url": "https://erp.exemplo.gov.br",
        "authentication": {
          "type": "bearer",
          "env_var": "ERP_API_TOKEN"
        },
        "timeout_seconds": 15,
        "headers": {
          "Accept": "application/json"
        },
        "operations": [
          {
            "id": "consultar_fornecedor",
            "label": "Consultar fornecedor",
            "method": "GET",
            "path": "/api/fornecedores/{cnpj}",
            "path_params": ["cnpj"],
            "query_params": ["ativo"],
            "body_fields": []
          }
        ]
      }
    ]
  }
}
```

## 5. Contrato global

`integrations.enabled`: booleano.

`items`: lista de integrações. IDs devem ser únicos.

Quando ausente ou desabilitado, nenhum cliente HTTP adicional deve ser materializado no projeto gerado.

## 6. Integração

Campos:

- `id`: identificador técnico seguro `[a-z][a-z0-9_]*`;
- `label`: nome visual obrigatório;
- `base_url`: URL absoluta `http` ou `https`; produção deverá preferir HTTPS;
- `authentication`: configuração fechada de autenticação;
- `timeout_seconds`: inteiro entre 1 e 120, default 15;
- `headers`: mapa de headers estáticos não secretos;
- `operations`: lista de operações.

Headers proibidos no mapa estático quando representarem segredo, incluindo `Authorization`. Credenciais devem vir de variável de ambiente.

## 7. Autenticação

Modos:

- `none`
- `basic`
- `bearer`
- `api_key`

### none

Sem credencial.

### basic

Referências:

- `username_env_var`
- `password_env_var`

### bearer

Referência:

- `env_var`

### api_key

Campos:

- `env_var`
- `location`: `header` ou `query`
- `name`: nome do header/query parameter

Nenhum valor secreto será salvo em `estrutura_json`.

## 8. Operações

Métodos permitidos:

- GET
- POST
- PUT
- PATCH
- DELETE

Campos:

- `id`
- `label`
- `method`
- `path`
- `path_params`
- `query_params`
- `body_fields`

O path deve ser relativo à `base_url` e pode conter placeholders declarados, por exemplo `/fornecedores/{cnpj}`.

Todo placeholder usado no path deve existir em `path_params`, e todo `path_param` deve existir no path.

GET e DELETE não terão body configurável na GEN-056.

## 9. Runtime gerado

Quando houver Integration Center ativo, gerar:

```text
<projeto>/integrations/
    __init__.py
    client.py
    config.py
```

O runtime deve usar biblioteca HTTP explicitamente adicionada ao `requirements.txt`. A implementação inicial adotará `httpx` síncrono para manter API clara, timeout explícito e independência do DjangoForge.

Artefatos esperados:

- configuração materializada sem secrets;
- `IntegrationClient`;
- resolução de credenciais via `os.environ`;
- montagem segura de URL/path/query/body;
- timeout por integração;
- `IntegrationConfigurationError`;
- `IntegrationRequestError`;
- `IntegrationResponseError`;
- retorno estruturado com status, headers e JSON/texto.

Nenhuma chamada externa será feita durante geração, `manage.py check` ou import do módulo.

## 10. API Python do runtime

Exemplo pretendido:

```python
from projeto.integrations import integrations

response = integrations.erp_corporativo.consultar_fornecedor(
    path={"cnpj": "12345678000199"},
    query={"ativo": True},
)

data = response.json()
```

A API final poderá ser refinada durante GEN-056.3, mantendo contrato determinístico e testável.

## 11. Interface visual

Adicionar `Integration Center` ao workspace depois de API Designer.

Tela:

### Cabeçalho

- Integrações ativas;
- botão Nova integração;
- Salvar.

### Sidebar

Lista das integrações cadastradas.

### Editor da integração

- ID;
- nome;
- base URL;
- autenticação;
- nomes das variáveis de ambiente;
- timeout;
- headers.

### Operações

Cada integração poderá possuir várias operações:

- ID;
- nome;
- método;
- path;
- parâmetros de path;
- parâmetros de query;
- campos JSON do body.

A UI deve mostrar preview do request, mas nunca valor de secret.

## 12. Validação

Novo módulo:

`sistema/integration_center.py`

Responsável por normalizar e validar o contrato.

Validações mínimas:

- IDs seguros e únicos;
- URL absoluta válida;
- esquema apenas http/https;
- timeout 1..120;
- autenticação conhecida;
- nomes de env vars seguros;
- `Authorization` proibido como header estático;
- operação com ID único dentro da integração;
- método conhecido;
- path relativo e sem URL absoluta;
- placeholders consistentes;
- parâmetros seguros e únicos;
- GET/DELETE sem body;
- configuração determinística.

Modo strict será usado para salvar/gerar/release. Modo tolerante poderá abrir drafts antigos sem impedir acesso à interface.

## 13. Segurança

O Integration Center não deve transformar o DjangoForge em cofre de segredos.

Exemplo gerado em `.env.example`:

```text
ERP_API_TOKEN=
```

O valor real será configurado no ambiente do sistema gerado.

Logs nunca devem imprimir Authorization, senha, bearer token ou API key.

## 14. Compatibilidade

Sem `integrations` ou com `enabled=false`:

- nenhuma dependência HTTP nova;
- nenhum pacote `integrations` gerado;
- nenhuma mudança funcional no sistema produzido pela GEN-055.

A GEN-056 não altera os contratos de API Designer, RBAC, Workflow, Business Rules, CRUD Designer ou Form Designer.

## 15. Fases

### GEN-056.1 — Contract & Validator

- `integration_center.py`;
- normalização;
- validação strict/tolerant;
- testes unitários.

### GEN-056.2 — Integration Center UI

- backend draft;
- tela visual;
- rotas;
- workspace;
- testes de persistência e autorização.

### GEN-056.3 — Generated Integration Runtime

- `httpx` condicional;
- pacote `integrations`;
- env vars;
- cliente HTTP;
- testes do código gerado.

### GEN-056.4 — Regression & Promotion

- regressão completa;
- teste manual em sistema gerado;
- validação de secrets/env;
- promoção para master somente após aprovação.

## 16. Critérios de aceite

- integração pode ser criada e salva visualmente;
- operações HTTP são configuráveis sem código;
- contrato inválido falha fechado;
- secrets não aparecem no draft;
- runtime lê secrets do ambiente;
- sistema gerado consegue executar uma chamada HTTP configurada;
- erros HTTP/timeout/configuração são distinguíveis;
- nenhuma integração => saída equivalente à GEN-055;
- suíte anterior continua passando.
