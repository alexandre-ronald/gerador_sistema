# GEN-053 — Workflow Engine

## Objetivo

Adicionar ao DjangoForge um mecanismo declarativo de workflow por entidade, permitindo modelar estados e transições de negócio de forma visual, segura e materializável no sistema Django gerado.

O Workflow Engine deve complementar o Business Rules Engine da GEN-052, sem duplicar suas responsabilidades. Regras continuam responsáveis por validações e ajustes de valores. Workflow passa a controlar evolução de estado.

## Princípios

1. **Declarativo, não programável**
   - Nenhum Python, SQL, JavaScript, template arbitrário, `eval` ou `exec`.

2. **Estado explícito**
   - Cada workflow opera sobre exatamente um campo de estado da entidade.

3. **Transições fechadas**
   - Apenas transições cadastradas podem alterar o estado quando um workflow está ativo.

4. **Fail closed**
   - Estado, transição, campo, origem ou destino desconhecido deve ser rejeitado.

5. **Compatibilidade retroativa**
   - Entidade sem configuração de workflow mantém exatamente o comportamento legado da GEN-052.

6. **Independência do sistema gerado**
   - Toda lógica necessária será compilada para o projeto Django gerado.

7. **Integração com Business Rules**
   - Regras de negócio podem validar operações antes/depois da preparação da transição, mas workflow não executa código arbitrário.

8. **Determinismo**
   - Estados e transições usam IDs estáveis e configuração normalizada.

## Escopo inicial

A GEN-053 implementará workflows de máquina de estados simples por entidade.

### Incluído

- um workflow por entidade;
- um campo de estado por workflow;
- lista declarativa de estados;
- estado inicial;
- estados finais;
- transições origem → destino;
- rótulo e ID estável de transição;
- ativação/desativação de workflow;
- ativação/desativação de transição;
- confirmação opcional da transição;
- exposição das ações válidas na interface gerada;
- proteção contra mudança manual de estado fora das transições;
- integração com CRUD gerado;
- histórico mínimo de transições no runtime gerado;
- validação e geração seguras.

### Não incluído

- múltiplos workflows simultâneos na mesma entidade;
- paralelismo, forks ou joins;
- BPMN;
- timers ou agendamentos;
- jobs assíncronos;
- chamadas HTTP;
- envio de e-mail;
- webhooks;
- aprovações por múltiplos usuários;
- RBAC por transição (GEN-054);
- SLA;
- escalonamento;
- subprocessos;
- compensações;
- scripts personalizados;
- condições arbitrárias em Python.

## Contrato persistido

A configuração ficará no draft `VersaoGeracao.numero=0`, em:

```json
{
  "workflows": {
    "Pedido": {
      "enabled": true,
      "state_field": "status",
      "initial_state": "rascunho",
      "states": [
        {
          "id": "rascunho",
          "label": "Rascunho",
          "final": false,
          "order": 0
        },
        {
          "id": "aprovado",
          "label": "Aprovado",
          "final": true,
          "order": 1
        }
      ],
      "transitions": [
        {
          "id": "aprovar",
          "label": "Aprovar",
          "from": ["rascunho"],
          "to": "aprovado",
          "enabled": true,
          "confirm": true,
          "confirm_message": "Confirmar aprovação?",
          "order": 0
        }
      ]
    }
  }
}
```

## Campo de estado

O campo escolhido deve:

- pertencer à própria entidade;
- não usar lookup com `__`;
- ser um campo simples suportado;
- inicialmente suportar `CharField`, `TextField`, `SlugField` ou tipos equivalentes textuais;
- ser editável estruturalmente;
- não ser `ManyToManyField`, arquivo, imagem ou relacionamento;
- não aceitar traversal de relacionamento.

A primeira implementação persistirá no campo o `id` do estado, não o label.

## Estados

Cada estado deve possuir:

- `id`: identificador estável e seguro;
- `label`: nome exibido;
- `final`: booleano;
- `order`: inteiro para apresentação.

Regras:

- IDs não podem repetir;
- IDs não podem conter `__`, `.`, `/` ou `\\`;
- deve existir pelo menos um estado;
- exatamente um `initial_state` deve apontar para estado existente;
- estado final pode existir sem transições de saída;
- estados finais não são obrigatórios na primeira versão.

## Transições

Cada transição deve possuir:

- `id` estável;
- `label`;
- `from`: lista não vazia de estados de origem;
- `to`: estado destino;
- `enabled`;
- `confirm`;
- `confirm_message` opcional;
- `order`.

Regras:

- origem e destino devem existir;
- uma transição não pode ter ID duplicado;
- transições desabilitadas não aparecem nem executam;
- `from` não pode ficar vazio;
- auto-transição será permitida, mas explícita;
- estado final não poderá ter transição de saída por padrão na GEN-053;
- múltiplas transições podem compartilhar origem e destino, desde que tenham IDs distintos.

## Semântica de runtime

### Criação

Quando a entidade tem workflow ativo:

1. objeto novo recebe `initial_state` se o campo estiver vazio;
2. tentativa de criação com outro estado explícito será rejeitada, salvo se já coincidir com `initial_state`;
3. Business Rules `before_create` e `before_save` continuam funcionando;
4. o workflow não deve provocar execução duplicada de regras.

### Atualização normal

Quando workflow está ativo:

- formulário CRUD normal não poderá alterar diretamente o `state_field`;
- alteração manual do estado no POST deve ser ignorada ou rejeitada de modo determinístico;
- demais campos continuam editáveis normalmente.

### Execução de transição

Uma transição só pode ocorrer se:

- workflow estiver habilitado;
- transição existir e estiver habilitada;
- estado atual estiver presente em `from`;
- destino existir;
- objeto não estiver em estado incompatível.

Ao executar:

1. carregar objeto atual;
2. validar transição;
3. aplicar estado destino;
4. validar Business Rules aplicáveis sem duplicação;
5. salvar de forma transacional;
6. registrar histórico mínimo;
7. redirecionar para detalhe ou lista com mensagem clara.

## Histórico mínimo de transição

O sistema gerado deve possuir modelo próprio por aplicação ou infraestrutura compartilhada capaz de registrar:

- modelo/entidade;
- object_id;
- transition_id;
- from_state;
- to_state;
- usuário quando autenticado;
- timestamp.

A GEN-053 não exigirá UI completa de auditoria, mas o registro deve existir e ser testável.

## Designer visual

Nova etapa **Workflow** no workspace, após Business Rules.

### Área principal

- seletor de entidade;
- toggle Workflow ativo;
- seletor do campo de estado;
- seletor do estado inicial;
- painel de estados;
- painel de transições;
- resumo visual do fluxo;
- botão salvar.

### Editor de estados

Permite:

- adicionar;
- renomear label;
- definir ID na criação;
- marcar final;
- ordenar;
- remover quando não referenciado por transições.

### Editor de transições

Permite:

- adicionar;
- duplicar;
- remover;
- definir nome/ID;
- escolher uma ou mais origens;
- escolher destino;
- habilitar/desabilitar;
- confirmação opcional;
- mensagem de confirmação;
- ordenação.

### Resumo visual

Na GEN-053 pode ser lista/fluxo visual simples; não é necessário canvas BPMN.

Exemplo:

```text
Rascunho
  └─ Aprovar → Aprovado
  └─ Cancelar → Cancelado
```

## Validação

O validador deve operar em modos estrito e tolerante, seguindo o padrão das GENs anteriores.

### Estrito

Usado no salvamento e geração. Rejeita:

- entidade desconhecida;
- campo de estado inexistente/inseguro/incompatível;
- estado duplicado;
- transição duplicada;
- origem inexistente;
- destino inexistente;
- estado inicial inexistente;
- transição saindo de estado final;
- tipos inválidos;
- valores booleanos/integer fora do contrato.

### Tolerante

Usado somente para exibição de configurações antigas/stale no Designer. Nunca deve persistir silenciosamente configuração alterada.

## Integração com GEN-052

Business Rules e Workflow têm responsabilidades distintas:

- **Business Rules**: validação e transformação de dados;
- **Workflow**: controle de transição de estado.

A GEN-053 não adicionará condição avançada própria nas transições inicialmente. Quando necessário, uma evolução posterior poderá referenciar regras declarativas existentes por ID.

## Runtime gerado

Cada app gerado deverá conter algo equivalente a:

```text
<app>/workflow.py
```

Responsabilidades:

- constantes normalizadas de workflow;
- descoberta do workflow da classe;
- obtenção do estado atual;
- listagem de transições disponíveis;
- validação de transição;
- aplicação da transição;
- erro específico e seguro;
- nenhuma execução dinâmica de código.

O runtime deve ser fechado e testável isoladamente.

## Integração com CRUD gerado

Quando houver workflow:

- Create aplica estado inicial;
- Form Designer continua definindo apresentação;
- state_field fica readonly/hidden na edição normal;
- Detail exibe estado atual e ações de transição válidas;
- List pode continuar exibindo o campo normalmente;
- endpoint POST dedicado executa transição;
- Delete continua submetido às regras da GEN-052.

## Segurança

É proibido no contrato ou runtime:

- `eval`;
- `exec`;
- import dinâmico configurável;
- SQL bruto configurável;
- nomes de campos com traversal;
- métodos configuráveis por string;
- templates arbitrários configuráveis;
- URLs externas configuráveis nesta GEN.

## Compatibilidade

Entidade sem workflow:

- não muda formulário;
- não muda CRUD;
- não muda URLs;
- não cria comportamento extra;
- mantém comportamento exato da GEN-052.

## Fases

### GEN-053.1 — Contract & Validator

- `sistema/workflow.py`;
- normalização;
- validação de metadata;
- validação de estados/transições;
- testes unitários do contrato.

### GEN-053.2 — Workflow Designer

- backend;
- rotas;
- UI visual;
- persistência no draft;
- integração no workspace;
- testes de UI/persistência.

### GEN-053.3 — Generated Workflow Runtime

- contexto de geração;
- `<app>/workflow.py`;
- estado inicial;
- proteção contra alteração direta;
- endpoint de transição;
- ações no detalhe;
- histórico mínimo;
- integração com Business Rules;
- testes dos artefatos gerados.

### GEN-053.4 — Regression & Promotion

- testes completos;
- geração real;
- validação manual;
- congelamento;
- promoção fast-forward para `master`.

## Critérios de aceite

A GEN-053 somente poderá ser promovida quando:

1. workflow inexistente mantiver comportamento GEN-052;
2. estado inicial for aplicado corretamente;
3. mudança manual de estado for bloqueada;
4. somente transições válidas forem executáveis;
5. transições inválidas forem rejeitadas com mensagem clara;
6. estados finais não aceitarem saída;
7. histórico mínimo for registrado;
8. Business Rules continuarem funcionando sem duplicidade;
9. Form Designer e CRUD Designer não regredirem;
10. `python manage.py check` e suíte completa passarem;
11. sistema realmente gerado passar `manage.py check`;
12. validação manual for aprovada antes da promoção.
