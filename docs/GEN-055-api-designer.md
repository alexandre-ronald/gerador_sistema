# GEN-055 — API Designer

## Status

Draft 0.1

Baseline de origem validado: GEN-054 — RBAC / Permission Designer

SHA base: `1cd4599f449154fa4ea8bc08bedbba1cf4ff1259`

Branch: `gen-055-api-designer`

---

## 1. Objetivo

Adicionar ao DjangoForge um **API Designer declarativo** capaz de configurar e gerar APIs REST seguras para as entidades do sistema, usando Django REST Framework (DRF), sem exigir escrita manual de serializers, viewsets, routers ou regras de autorização.

A GEN-055 transforma os flags estruturais já existentes:

- `Sistema.gerar_api_rest`
- `Entidade.gerar_endpoints_api`

em uma capacidade efetiva de geração, mantendo separadas as responsabilidades:

- **Model Designer** → estrutura de dados;
- **Form Designer** → experiência de formulário HTML;
- **CRUD Designer** → experiência CRUD HTML;
- **Business Rules** → validação e transformação de dados;
- **Workflow** → estados e transições;
- **RBAC** → quem pode executar ações;
- **API Designer** → como a entidade é exposta por HTTP/JSON.

---

## 2. Princípios

### 2.1 Declarativo

Nenhuma configuração da API pode aceitar:

- Python arbitrário;
- SQL arbitrário;
- JavaScript;
- expressões `eval`/`exec`;
- imports definidos pelo usuário;
- serializers escritos manualmente no Designer;
- filtros ou lookups livres não validados.

### 2.2 Fail closed

Configurações inválidas devem falhar na validação antes da geração.

São inválidos, entre outros:

- entidade inexistente;
- campo inexistente;
- método desconhecido;
- campo gravável não exposto;
- campo somente leitura usado como gravável;
- ordenação por campo não autorizado;
- busca em tipo não suportado;
- endpoint duplicado;
- prefixo inseguro.

### 2.3 Compatibilidade

Se não existir configuração `apis` no draft, a GEN-054 deve permanecer funcional sem regressão.

A ausência do API Designer **não pode alterar**:

- CRUD HTML;
- Form Designer;
- Business Rules;
- Workflow;
- RBAC;
- Dashboard;
- geração de sistemas que não utilizam API.

### 2.4 Django/DRF nativo

A implementação gerada deve usar os componentes padrão do Django REST Framework:

- `ModelSerializer`;
- `ModelViewSet` ou base equivalente segura;
- routers DRF;
- `IsAuthenticated`;
- permissões Django/RBAC;
- `SearchFilter`;
- `OrderingFilter`.

DRF recomenda ViewSets para agrupar operações relacionadas e routers para registrar URLs automaticamente. As permissões são verificadas antes da execução do corpo da view. A GEN-055 utilizará esses mecanismos em vez de criar um framework HTTP paralelo.

### 2.5 Independência do sistema gerado

A aplicação gerada não pode depender do DjangoForge em runtime.

Todo contrato necessário deve ser compilado para arquivos locais do sistema gerado.

---

## 3. Relação com os flags atuais

### Sistema

`Sistema.gerar_api_rest = False`

Resultado:

- nenhuma dependência DRF adicionada;
- nenhuma URL `/api/` adicionada;
- nenhuma configuração API materializada.

`Sistema.gerar_api_rest = True`

Resultado:

- sistema torna-se elegível à geração DRF;
- API Designer pode configurar entidades elegíveis.

### Entidade

`Entidade.gerar_endpoints_api = False`

A entidade não pode ser publicada pela API.

`Entidade.gerar_endpoints_api = True`

A entidade torna-se elegível no API Designer.

O API Designer não deve ativar silenciosamente `gerar_endpoints_api` em entidade que não foi marcada estruturalmente no Model Designer.

---

## 4. Persistência

A configuração será armazenada no draft atual:

`VersaoGeracao.numero = 0`

chave:

`estrutura_json["apis"]`

Nenhuma migration do DjangoForge será criada na GEN-055.

### Estrutura proposta

```json
{
  "apis": {
    "enabled": true,
    "prefix": "api",
    "version": "v1",
    "authentication": "session_basic",
    "entities": {
      "Solicitacao": {
        "enabled": true,
        "endpoint": "solicitacoes",
        "operations": {
          "list": true,
          "retrieve": true,
          "create": true,
          "update": true,
          "partial_update": true,
          "destroy": false
        },
        "fields": [
          "id",
          "titulo",
          "setor",
          "valor_estimado",
          "status"
        ],
        "read_only_fields": [
          "id",
          "status"
        ],
        "search_fields": [
          "titulo",
          "setor"
        ],
        "ordering_fields": [
          "titulo",
          "valor_estimado",
          "status"
        ],
        "default_ordering": ["titulo"],
        "page_size": 25
      }
    }
  }
}
```

---

## 5. Configuração global da API

### `enabled`

Booleano.

Somente pode ser `true` quando `Sistema.gerar_api_rest = True`.

### `prefix`

Prefixo base da URL.

Default:

`api`

Regras:

- identificador URL seguro;
- sem `/` inicial/final;
- sem `..`;
- sem `__`;
- sem espaços;
- apenas letras ASCII, números, `_` e `-`.

### `version`

Versão textual segura da API.

Default:

`v1`

Primeira versão aceita:

- `v1`, `v2`, etc.;
- identificador seguro;
- não implementa negociação complexa de versão nesta GEN.

URL final conceitual:

`/<prefix>/<version>/...`

Exemplo:

`/api/v1/solicitacoes/`

### `authentication`

Valores permitidos na GEN-055:

- `session`
- `basic`
- `session_basic`

Default:

`session_basic`

Não serão implementados nesta GEN:

- JWT;
- OAuth2;
- API keys;
- OIDC;
- autenticação pública anônima.

Esses mecanismos ficam para Integration Center/Security evolution posterior.

---

## 6. Entidades da API

Somente entidades com:

`gerar_endpoints_api = True`

podem existir em `apis.entities`.

Cada entidade terá:

- `enabled`;
- `endpoint`;
- operações;
- campos expostos;
- campos somente leitura;
- busca;
- ordenação;
- ordenação padrão;
- paginação.

---

## 7. Endpoint

Campo:

`endpoint`

Exemplo:

`solicitacoes`

Regras:

- obrigatório quando entidade ativa;
- seguro para URL;
- único dentro da API;
- sem `/`;
- sem `..`;
- sem `__`;
- normalização determinística;
- não pode conflitar com endpoint de outra entidade.

O Designer exibe o preview:

`/api/v1/solicitacoes/`

---

## 8. Operações suportadas

Contrato fechado:

- `list`
- `retrieve`
- `create`
- `update`
- `partial_update`
- `destroy`

Correspondência HTTP/DRF:

| Operação | HTTP |
|---|---|
| list | GET coleção |
| retrieve | GET item |
| create | POST |
| update | PUT |
| partial_update | PATCH |
| destroy | DELETE |

Nenhuma operação arbitrária pode ser declarada na GEN-055.

Custom actions `@action` ficam fora de escopo inicialmente.

---

## 9. Campos expostos

`fields` define o contrato JSON de entrada/saída do serializer.

Regras:

- somente campos reais da entidade;
- `id` pode ser incluído como campo automático;
- lista sem duplicação;
- ao menos um campo;
- relações serão inicialmente representadas por chave primária;
- sem serializer aninhado configurável nesta GEN.

### Tipos suportados

Todos os tipos já materializados pelo Model Designer podem ser serializados pelo `ModelSerializer`, respeitando as limitações de escrita do próprio modelo.

Arquivos e imagens seguem comportamento padrão DRF, sem upload avançado adicional.

---

## 10. Campos somente leitura

`read_only_fields`

Regras:

- precisa ser subconjunto de `fields`;
- campos controlados por Workflow devem ser automaticamente recomendados como read-only;
- `id` será read-only;
- campos de auditoria gerados podem ser read-only;
- campo read-only não poderá ser alterado por POST/PUT/PATCH.

### Integração Workflow

Se uma entidade possuir Workflow ativo, o `state_field` não deverá ser gravável pela API CRUD.

Alterações de estado continuam sob responsabilidade do Workflow Engine.

Nesta primeira GEN, ações de Workflow não serão expostas automaticamente como endpoints REST customizados.

Isso evita duplicar o contrato do Workflow.

---

## 11. Busca

`search_fields`

Somente tipos textuais serão aceitos inicialmente:

- `CharField`
- `TextField`
- `EmailField`
- `URLField`

A implementação utilizará `SearchFilter` do DRF.

Query esperada:

`?search=notebook`

Não aceitar lookups definidos pelo usuário (`__icontains`, etc.).

---

## 12. Ordenação

`ordering_fields`

Lista fechada de campos permitidos.

Query:

`?ordering=titulo`

ou:

`?ordering=-valor_estimado`

`default_ordering` deve conter apenas campos presentes em `ordering_fields`, admitindo prefixo `-`.

A implementação usará `OrderingFilter` do DRF.

---

## 13. Paginação

Configuração por entidade:

`page_size`

Faixa inicial permitida:

`1..500`

Default:

`25`

A paginação gerada deve ser determinística e não permitir ao cliente elevar ilimitadamente o page size nesta GEN.

---

## 14. Autorização e integração com GEN-054

A API não pode criar um segundo modelo de autorização.

### Quando RBAC estiver desativado

Usar:

- usuário autenticado;
- permissões Django do modelo conforme a operação.

Mapeamento:

| API | Django permission |
|---|---|
| list | view |
| retrieve | view |
| create | add |
| update | change |
| partial_update | change |
| destroy | delete |

### Quando RBAC estiver ativo

Além das permissões Django base, aplicar GEN-054:

| API | RBAC CRUD action |
|---|---|
| list | list |
| retrieve | view |
| create | create |
| update | update |
| partial_update | update |
| destroy | delete |

`is_superuser=True` preserva bypass já definido pela GEN-054.

Usuário sem papel aplicável continua fail-closed quando RBAC estiver ativo.

---

## 15. Business Rules na API

A API deve respeitar a GEN-052.

### Create

Antes da persistência:

- `before_create`;
- `before_save` conforme contrato existente e sem duplicação.

### Update/PATCH

Antes da persistência:

- `before_update`;
- `before_save` conforme contrato existente e sem duplicação.

### Delete

Antes da exclusão:

- `before_delete`.

A implementação deve reutilizar o runtime gerado existente, não copiar a lógica das Business Rules para o serializer.

---

## 16. Workflow na API

Na GEN-055:

### Incluído

- proteger state field como read-only;
- criação aplica estado inicial do Workflow;
- API CRUD não pode realizar mudança direta de estado;
- Workflow continua consistente mesmo quando registro nasce pela API.

### Não incluído

- endpoint REST de transição;
- discovery REST de transições;
- aprovação por endpoint customizado;
- hypermedia/HATEOAS de Workflow.

Essas ações poderão entrar numa evolução posterior, após estabilização do contrato base da API.

---

## 17. Arquivos gerados

Para módulos com entidades API ativas:

```text
<app>/serializers.py
<app>/api_views.py
<app>/api_urls.py
```

O projeto raiz incluirá as URLs da API somente quando a API estiver habilitada.

### `serializers.py`

Responsável por:

- `ModelSerializer`;
- fields;
- read_only_fields.

### `api_views.py`

Responsável por:

- ViewSets;
- métodos permitidos;
- autenticação;
- Django permissions;
- RBAC;
- SearchFilter;
- OrderingFilter;
- paginação;
- integração Business Rules;
- integração Workflow create.

### `api_urls.py`

Responsável por:

- router DRF;
- registro declarativo dos endpoints.

---

## 18. Dependências do sistema gerado

Quando API ativa:

`requirements.txt` deve adicionar:

```text
djangorestframework>=3.16,<4
```

E `INSTALLED_APPS` deve adicionar:

```python
'rest_framework'
```

Quando API não estiver ativa, essas alterações não devem ocorrer.

---

## 19. Designer visual

Nova etapa no Workspace:

`API Designer`

Posição sugerida:

```text
Model Designer
Form Designer
CRUD Designer
Business Rules
Workflow Designer
Permission Designer
API Designer
Dashboard Designer
```

### Cabeçalho

- API ativa;
- prefixo;
- versão;
- autenticação;
- preview da URL base.

### Sidebar

Lista somente entidades elegíveis (`gerar_endpoints_api=True`).

### Editor da entidade

- endpoint ativo;
- path;
- operações;
- campos expostos;
- campos read-only;
- campos de busca;
- campos de ordenação;
- ordenação default;
- page size;
- preview dos endpoints HTTP.

### Preview conceitual

Exemplo:

```text
GET     /api/v1/solicitacoes/
POST    /api/v1/solicitacoes/
GET     /api/v1/solicitacoes/{id}/
PUT     /api/v1/solicitacoes/{id}/
PATCH   /api/v1/solicitacoes/{id}/
DELETE  /api/v1/solicitacoes/{id}/
```

Somente operações ativadas aparecem.

---

## 20. Validador

Novo módulo conceitual:

`sistema/api_designer.py`

Responsabilidades:

- normalização;
- strict/tolerant;
- segurança de IDs/paths;
- validação global;
- validação de entidades;
- validação de operações;
- campos;
- read-only;
- search;
- ordering;
- paginação;
- conflitos de endpoint.

### Strict

Obrigatório para:

- salvar;
- gerar;
- validar release.

### Tolerant

Somente para abrir Designer com configuração antiga/stale sem quebrar a tela.

---

## 21. Contrato normalizado

Estrutura normalizada deve ser determinística:

- entidades ordenadas por nome;
- operações na ordem fixa do contrato;
- campos preservando ordem configurada;
- listas sem duplicação;
- endpoint normalizado;
- defaults explícitos.

Isso é importante para:

- versionamento;
- diffs;
- testes;
- futuras releases.

---

## 22. Segurança

### Obrigatório

- autenticação por padrão;
- autorização server-side;
- nenhuma confiança em UI;
- nenhuma escrita direta no state field do Workflow;
- nenhuma exposição automática de campos não selecionados;
- nenhuma operação não configurada;
- nenhum lookup arbitrário;
- erros HTTP coerentes;
- validação antes de salvar contrato.

### Respostas esperadas

- não autenticado: `401` ou `403` conforme autenticador DRF aplicável;
- autenticado sem autorização: `403`;
- recurso inexistente: `404`;
- payload inválido: `400`.

---

## 23. Fora de escopo da GEN-055

- JWT;
- OAuth2/OIDC;
- API Key;
- API pública anônima;
- rate limit customizado;
- throttling Designer;
- cache Designer;
- CORS Designer;
- GraphQL;
- gRPC;
- webhooks;
- custom actions;
- endpoints Workflow;
- serializers aninhados configuráveis;
- field-level RBAC;
- row-level permissions;
- API version negotiation avançada;
- OpenAPI Designer completo;
- geração de SDK;
- integração externa.

Esses itens pertencem a evoluções posteriores, especialmente GEN-056 Integration Center.

---

## 24. Fases

### GEN-055.1 — Contract & Validator

- contrato normalizado;
- constantes;
- segurança de prefix/version/endpoint;
- operações;
- campos/read-only;
- search/order;
- paginação;
- strict/tolerant;
- integração metadata;
- testes unitários.

### GEN-055.2 — API Designer

- backend;
- rotas;
- persistência draft;
- UI;
- entidades elegíveis;
- operações;
- fields/read-only;
- search/order;
- preview;
- integração Workspace;
- testes UI/persistência.

### GEN-055.3 — Generated API Runtime

- requirements DRF;
- settings;
- serializers;
- viewsets;
- routers;
- root URLs;
- Django permissions;
- RBAC;
- Business Rules;
- Workflow create/read-only state;
- testes do artefato gerado.

### GEN-055.4 — Regression & Promotion

- targeted tests;
- suíte completa;
- geração real;
- migrations do sistema gerado;
- `manage.py check`;
- testes HTTP reais;
- validação manual;
- comparação com baseline;
- congelamento;
- fast-forward para master.

---

## 25. Critérios de aceite

A GEN-055 somente poderá ser promovida quando:

1. sistema sem API preservar comportamento GEN-054;
2. entidade não elegível não puder ser exposta;
3. endpoint inválido/duplicado for rejeitado;
4. operações desconhecidas forem rejeitadas;
5. serializer expuser somente campos configurados;
6. read-only não puder ser escrito;
7. campo de estado do Workflow não puder ser alterado diretamente;
8. criação por API aplicar estado inicial do Workflow;
9. Business Rules funcionarem em create/update/delete via API;
10. operação desativada não possuir rota executável equivalente;
11. usuário não autenticado for bloqueado;
12. Django permissions forem aplicadas;
13. RBAC restringir API de acordo com GEN-054;
14. múltiplos papéis produzirem união das permissões;
15. superuser permanecer autorizado;
16. SearchFilter aceitar somente campos configurados;
17. OrderingFilter aceitar somente campos configurados;
18. paginação respeitar contrato;
19. aplicação gerada possuir `serializers.py`, `api_views.py`, `api_urls.py` quando aplicável;
20. `requirements.txt` incluir DRF somente quando API ativa;
21. `INSTALLED_APPS` incluir `rest_framework` somente quando API ativa;
22. DjangoForge `python manage.py check` passar;
23. suíte completa DjangoForge passar;
24. sistema gerado `python manage.py check` passar;
25. testes HTTP reais da API passarem;
26. validação manual ser aprovada.

---

## 26. Decisão arquitetural

A GEN-055 não será apenas um botão "gerar API".

Ela introduz um contrato de API versionável e visualmente configurável, compilado para DRF, mantendo a arquitetura do DjangoForge:

```text
Design
  Model
  Form
  CRUD
  Rules
  Workflow
  RBAC
  API
  Dashboard

        ↓

Build
  Validator
  Compiler
  Tests
  Release

        ↓

Run
  Runtime Agent
  Health
  Environments
```

A API passa a ser mais uma projeção segura do mesmo domínio, e não um segundo sistema paralelo.
