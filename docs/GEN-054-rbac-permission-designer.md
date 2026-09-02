# GEN-054 — RBAC / Permission Designer

## Objetivo

Adicionar ao DjangoForge uma camada declarativa e visual de autorização baseada em papéis (RBAC), materializável no sistema Django gerado, integrada aos CRUDs, Workflow Engine e autenticação padrão do Django.

A GEN-054 controla **quem pode executar uma ação**. Ela não substitui Business Rules nem Workflow:

- Business Rules: valida dados e transforma valores.
- Workflow: controla estados e transições.
- RBAC: controla autorização de usuários/papéis para acessar recursos e executar ações.

## Princípios

1. **Declarativo** — sem Python, SQL, JavaScript, expressões ou permissões arbitrárias.
2. **Fail closed** — papel, entidade, ação ou transição desconhecida deve ser rejeitada.
3. **Compatibilidade** — ausência de configuração RBAC preserva exatamente o comportamento da GEN-053.
4. **Runtime independente** — o sistema gerado não depende do DjangoForge em execução.
5. **Django-native** — autenticação continua baseada em `django.contrib.auth`; a configuração gerada utiliza Groups/permissions e helpers explícitos.
6. **Menor privilégio quando RBAC estiver ativo** — ações não concedidas ficam bloqueadas.
7. **Sem duplicação de responsabilidade** — RBAC autoriza; Workflow decide se uma transição é estruturalmente possível.
8. **IDs estáveis e configuração determinística**.

## Escopo da GEN-054

### Incluído

- papéis (roles) declarativos;
- vínculo dos papéis com grupos Django;
- permissões por entidade;
- ações CRUD: `list`, `view`, `create`, `update`, `delete`;
- autorização de transições do Workflow por papel;
- papel de superusuário continua respeitando `is_superuser`;
- Permission Designer visual;
- persistência no draft;
- geração de runtime de autorização;
- proteção server-side das views geradas;
- ocultação de ações não autorizadas na UI gerada;
- testes de compatibilidade e segurança.

### Fora do escopo

- ABAC baseado em atributos;
- permissões por registro/objeto;
- condições Python;
- políticas por horário/IP/localização;
- hierarquia complexa de papéis;
- aprovação multiusuário;
- SSO/LDAP/OIDC;
- provisionamento externo de usuários;
- multi-tenant RBAC;
- permissões de campos individuais;
- delegação temporária.

## Persistência

A configuração permanece no draft:

```text
VersaoGeracao.numero = 0
estrutura_json["rbac"]
```

Contrato inicial:

```json
{
  "rbac": {
    "enabled": true,
    "roles": [
      {
        "id": "operador",
        "label": "Operador",
        "group": "Operadores",
        "order": 0
      },
      {
        "id": "gestor",
        "label": "Gestor",
        "group": "Gestores",
        "order": 1
      }
    ],
    "entities": {
      "Pedido": {
        "roles": {
          "operador": ["list", "view", "create", "update"],
          "gestor": ["list", "view", "create", "update", "delete"]
        },
        "transitions": {
          "aprovar": ["gestor"],
          "cancelar": ["gestor"]
        }
      }
    }
  }
}
```

## Papéis

Cada papel possui:

- `id` — identificador estável e seguro;
- `label` — nome apresentado no Designer;
- `group` — nome do Django Group correspondente no sistema gerado;
- `order` — ordenação visual.

Regras:

- IDs únicos;
- grupos não vazios;
- IDs não podem conter `__`, `.`, `/` ou `\\`;
- ordem inteira dentro dos limites do contrato;
- um usuário pode pertencer a vários grupos/papéis;
- permissões efetivas são a união dos papéis do usuário;
- `is_superuser=True` autoriza todas as ações.

## Ações de entidade

Ações permitidas inicialmente:

- `list`
- `view`
- `create`
- `update`
- `delete`

Não serão aceitos nomes de ações arbitrários.

Quando RBAC estiver habilitado e uma entidade possuir política declarada, qualquer ação não concedida ao usuário deve resultar em negação server-side.

## Integração com Workflow

A configuração de transições referencia o ID estável da transição já definida pela GEN-053.

Exemplo:

```json
"transitions": {
  "aprovar": ["gestor"],
  "cancelar": ["gestor", "operador"]
}
```

Execução de uma transição exige duas verificações independentes:

1. Workflow confirma que a transição é válida para o estado atual.
2. RBAC confirma que o usuário está autorizado a executar a transição.

A autorização nunca torna válida uma transição inválida estruturalmente.

Se uma entidade possuir Workflow mas nenhuma política de transição RBAC, a GEN-054 preservará o comportamento da GEN-053 para aquela transição, evitando regressão silenciosa em projetos existentes.

## Sem configuração

Se `estrutura_json["rbac"]` não existir, estiver vazio ou `enabled=false`:

- nenhum bloqueio RBAC adicional será gerado;
- CRUD mantém comportamento GEN-053;
- Workflow mantém comportamento GEN-053;
- templates continuam exibindo as ações existentes;
- nenhuma dependência adicional é necessária.

## Validator

A validação estrita deve rejeitar:

- estrutura principal inválida;
- `enabled` não booleano;
- papel duplicado;
- ID inseguro;
- label/group vazio;
- order inválido;
- entidade inexistente;
- papel inexistente referenciado por entidade;
- ação CRUD desconhecida;
- transição inexistente;
- papel inexistente referenciado por transição;
- tipos incompatíveis.

Modo tolerante será usado apenas para abrir configuração antiga/stale no Designer. Alterações só poderão ser persistidas após validação estrita.

## Permission Designer

Nova etapa no workspace após Workflow Designer.

### Área de papéis

- ativar/desativar RBAC;
- criar papel;
- editar label;
- definir Django Group;
- ordenar;
- duplicar;
- remover quando não houver referências ou após confirmação explícita.

### Matriz de permissões

Interface sugerida:

```text
                    Operador    Gestor
Pedidos
  Listar               ✓          ✓
  Visualizar            ✓          ✓
  Criar                 ✓          ✓
  Editar                ✓          ✓
  Excluir               -          ✓
```

### Workflow

Quando a entidade possuir Workflow:

```text
Transições            Operador    Gestor
Aprovar                  -          ✓
Cancelar                 ✓          ✓
```

O Designer deve trabalhar com IDs internos e apresentar labels amigáveis.

## Runtime gerado

Cada app com políticas RBAC terá helper equivalente a:

```text
<app>/permissions.py
```

Responsabilidades:

- configuração normalizada fechada;
- descobrir papéis do usuário pelos Django Groups;
- verificar ação de entidade;
- verificar transição;
- tratar usuário não autenticado;
- respeitar superuser;
- gerar erros claros de autorização;
- nenhuma execução dinâmica.

API conceitual:

```python
can_entity_action(user, entity, action)
can_transition(user, entity, transition_id)
require_entity_action(user, entity, action)
require_transition(user, entity, transition_id)
```

## CRUD gerado

Com RBAC ativo:

- ListView exige `list`;
- DetailView exige `view`;
- CreateView exige `create`;
- UpdateView exige `update`;
- DeleteView exige `delete`;
- botões/links são exibidos somente quando autorizados;
- proteção visual nunca substitui proteção server-side.

## Workflow gerado

Endpoint POST de transição:

1. autentica usuário;
2. verifica autorização RBAC quando configurada;
3. valida transição pelo Workflow;
4. executa Business Rules aplicáveis;
5. persiste mudança e histórico.

## Fases

### GEN-054.1 — Contract & Validator

- `sistema/rbac.py`;
- normalização de papéis;
- validação de ações CRUD;
- validação de entidades;
- validação de transições Workflow;
- modo strict/tolerant;
- testes unitários.

### GEN-054.2 — Permission Designer

- backend;
- rotas;
- UI;
- persistência draft;
- matriz entidade × papel;
- matriz transição × papel;
- integração no workspace;
- testes de UI/persistência.

### GEN-054.3 — Generated RBAC Runtime

- contexto do gerador;
- `permissions.py` gerado;
- proteção server-side CRUD;
- proteção das transições;
- visibilidade de ações nos templates;
- integração com Groups Django;
- testes de artefatos gerados.

### GEN-054.4 — Regression & Promotion

- suíte completa;
- geração real;
- `manage.py check` no artefato;
- validação manual;
- congelamento;
- fast-forward para master.

## Critérios de aceite

A GEN-054 só poderá ser promovida quando:

1. ausência de RBAC preservar integralmente a GEN-053;
2. roles inválidos forem rejeitados;
3. ações CRUD não autorizadas forem bloqueadas server-side;
4. botões não autorizados não forem exibidos;
5. usuário com múltiplos papéis receber a união das permissões;
6. superuser continuar autorizado;
7. transição autorizada por RBAC ainda depender do Workflow;
8. transição não autorizada for bloqueada;
9. Business Rules e Workflow não sofrerem execução duplicada;
10. Form, CRUD, Business Rules e Workflow Designers não regredirem;
11. `python manage.py check` passar;
12. suíte completa passar;
13. sistema gerado passar em `manage.py check`;
14. validação manual for aprovada.
