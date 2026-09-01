# GEN-052 — Business Rules Engine

## Objetivo

Adicionar ao DjangoForge um motor declarativo e seguro de regras de negócio, configurável por entidade e materializado no sistema Django gerado.

A GEN-052 transforma regras que hoje exigiriam edição manual de Python em contratos persistidos e validados pelo DjangoForge, sem permitir execução de código arbitrário.

## Princípios

1. **Declarativo, não programável** — nenhuma regra aceita Python, SQL, JavaScript ou template arbitrário.
2. **Fail closed** — operadores, campos, eventos e ações desconhecidos são rejeitados.
3. **Compatibilidade** — sem configuração de regras, a geração e o runtime permanecem iguais à GEN-051.
4. **Independência do sistema gerado** — as regras são compiladas para código/runtime local do projeto gerado; ele não depende do DjangoForge em execução.
5. **Campos validados** — toda referência a campo deve existir na entidade e ser compatível com o operador/ação.
6. **Ordem determinística** — regras possuem prioridade explícita e execução previsível.
7. **Erros compreensíveis** — violações devem produzir mensagens de validação adequadas ao usuário final.
8. **Sem efeitos externos nesta GEN** — e-mail, webhook, jobs e integrações ficam para Workflow/Integration Center.

## Escopo incluído

### Eventos

- `before_create`
- `before_update`
- `before_save`
- `before_delete`

Nesta GEN as regras atuam antes da persistência/remoção, permitindo validação e transformação segura dos dados.

### Condições

Uma regra pode ter zero ou mais condições combinadas por:

- `all` — todas precisam ser verdadeiras (AND)
- `any` — ao menos uma precisa ser verdadeira (OR)

Operadores iniciais:

- `eq`
- `neq`
- `gt`
- `gte`
- `lt`
- `lte`
- `contains`
- `starts_with`
- `ends_with`
- `is_empty`
- `is_not_empty`
- `is_true`
- `is_false`

Os operadores disponíveis dependem do tipo do campo.

### Fontes de valor

Comparações podem utilizar:

- valor literal tipado;
- outro campo da mesma entidade.

Não são permitidos lookups Django (`__`), caminhos relacionais, funções ou expressões.

### Ações

#### `reject`

Interrompe a operação com mensagem de validação configurada.

Exemplo: impedir aprovação quando `valor_total <= 0`.

#### `set_value`

Define um valor literal em um campo editável compatível.

Exemplo: ao criar pedido sem status, definir `status = "PENDENTE"`.

#### `copy_value`

Copia o valor de outro campo da mesma entidade.

Exemplo: copiar `data_solicitacao` para `data_referencia` sob determinada condição.

### Estado da regra

Cada regra possui:

- `id` estável;
- `name`;
- `enabled`;
- `event`;
- `priority`;
- `condition_mode`;
- `conditions`;
- `actions`.

## Contrato persistido

As configurações ficam no draft `VersaoGeracao.numero=0`, em `estrutura_json["business_rules"]`.

```json
{
  "business_rules": {
    "Pedido": {
      "rules": [
        {
          "id": "validar_valor_aprovado",
          "name": "Valor obrigatório para aprovação",
          "enabled": true,
          "event": "before_save",
          "priority": 10,
          "condition_mode": "all",
          "conditions": [
            {
              "field": "status",
              "operator": "eq",
              "value_source": "literal",
              "value": "APROVADO"
            },
            {
              "field": "valor_total",
              "operator": "lte",
              "value_source": "literal",
              "value": 0
            }
          ],
          "actions": [
            {
              "type": "reject",
              "message": "Pedidos aprovados precisam ter valor maior que zero."
            }
          ]
        }
      ]
    }
  }
}
```

## Validação do contrato

O normalizador deve validar:

- entidade existente;
- `id` seguro e único dentro da entidade;
- evento permitido;
- prioridade inteira em faixa segura;
- modo `all|any`;
- campo existente;
- proibição de `__`, `.`, `/` e `\\` em referências de campo;
- operador compatível com o tipo do campo;
- fonte `literal|field`;
- campo de comparação existente quando `value_source=field`;
- literal compatível com o tipo quando aplicável;
- ação conhecida;
- campo alvo existente e editável;
- mensagem de rejeição não vazia;
- pelo menos uma ação por regra.

Modo tolerante deve ignorar referências obsoletas para permitir abrir o Designer após alterações estruturais. Modo estrito deve rejeitá-las ao salvar.

## Execução no sistema gerado

O gerador deverá materializar um módulo local de regras, por app, por exemplo:

`<app>/business_rules.py`

A execução será chamada explicitamente pelas views/formulários gerados nos eventos suportados.

Características:

- regras compiladas como estruturas constantes;
- evaluator fechado com operadores conhecidos;
- sem `eval`, `exec`, import dinâmico ou SQL;
- `reject` convertido em erro de validação/formulário;
- `set_value` e `copy_value` aplicados antes do `save()`;
- regras ordenadas por `priority` e depois por `id`;
- regras desabilitadas não executam.

## Integração com GEN-050 e GEN-051

### Form Designer

Erros `reject` devem aparecer no fluxo normal do formulário, preservando os layouts e metadados da GEN-050.

### CRUD Designer

Create/Update/Delete gerados pela GEN-051 devem disparar os eventos correspondentes sem alterar busca, filtros, ordenação, paginação ou ações configuradas.

## Interface visual planejada

Workspace ganha **Business Rules** após CRUD Designer.

Designer por entidade:

- seletor de entidade;
- lista ordenada de regras;
- criar/duplicar/remover;
- habilitar/desabilitar;
- nome, evento e prioridade;
- editor de condições;
- seletor AND/OR;
- editor de ações;
- resumo legível da regra;
- validação visual;
- Preview da lógica sem executar persistência;
- salvar no draft.

## Fora do escopo

- Python/SQL/JS arbitrário;
- regras entre entidades via joins;
- agregações;
- chamadas HTTP;
- e-mails;
- webhooks;
- tarefas assíncronas;
- agendamentos;
- aprovação multi-etapa;
- máquina de estados completa;
- permissões/RBAC;
- execução pós-commit;
- auditoria avançada de cada disparo;
- versionamento independente de regras.

Esses itens pertencem principalmente às GEN-053 Workflow Engine, GEN-054 RBAC e GEN-056 Integration Center.

## Fases

### GEN-052.1 — Contract & Validator

- `business_rules.py` no DjangoForge;
- constantes e compatibilidade de tipos;
- normalização tolerante/estrita;
- testes unitários do contrato;
- nenhum impacto no gerador.

### GEN-052.2 — Business Rules Designer

- endpoints owner-only;
- persistência no draft;
- interface visual;
- workspace navigation;
- testes de UI e persistência.

### GEN-052.3 — Generated Rules Runtime

- contexto do `GeradorService`;
- módulo `business_rules.py` gerado;
- integração Create/Update/Delete;
- validação amigável;
- testes de artefato real;
- fallback legado sem regras.

### GEN-052.4 — Regression & Promotion

- suíte completa;
- geração real;
- testes manuais das regras;
- comparação contra baseline GEN-051;
- promoção para `master` somente após validação.

## Critérios de aceite

A GEN-052 estará concluída quando:

1. regras puderem ser criadas visualmente sem código;
2. contratos inválidos forem rejeitados antes da geração;
3. sistema gerado executar regras de forma determinística e segura;
4. `reject` impedir operações com mensagem compreensível;
5. `set_value` e `copy_value` alterarem apenas campos autorizados;
6. nenhuma regra permitir lookup ou código arbitrário;
7. ausência de configuração preservar integralmente o comportamento GEN-051;
8. GEN-050 Form Designer e GEN-051 CRUD Designer continuarem funcionando;
9. testes novos e regressivos passarem;
10. validação manual do sistema gerado for aprovada.
