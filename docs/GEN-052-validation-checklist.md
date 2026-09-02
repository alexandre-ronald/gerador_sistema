# GEN-052 — Checklist de validação final

## Objetivo
Validar o Business Rules Engine de ponta a ponta antes da promoção para `master`.

## Pré-condições
- Branch: `gen-052-business-rules-engine`
- `python manage.py check` sem erros
- `python manage.py test` completo aprovado
- Sistema de teste com pelo menos uma entidade CRUD e campos texto, numérico e booleano

## Cenário A — reject / before_create
1. Criar regra `before_create` com condição simples.
2. Adicionar ação `reject` com mensagem clara.
3. Salvar o Designer.
4. Gerar a aplicação.
5. Tentar criar um registro que satisfaça a condição.

Resultado esperado:
- registro não é salvo;
- erro aparece no formulário;
- nenhum traceback/500;
- valor digitado permanece no formulário.

## Cenário B — set_value / before_create
1. Criar regra `before_create` com ação `set_value`.
2. Gerar novamente a aplicação.
3. Criar registro que satisfaça a regra.

Resultado esperado:
- registro é salvo;
- campo alvo recebe o valor definido pela regra;
- demais campos permanecem intactos.

## Cenário C — copy_value / before_update
1. Criar regra `before_update` com ação `copy_value`.
2. Editar um registro existente.

Resultado esperado:
- campo origem é copiado para o campo alvo antes do save;
- edição conclui normalmente;
- nenhum campo não relacionado é alterado.

## Cenário D — before_save
1. Criar regra `before_save` com `reject` ou `set_value`.
2. Testar criação.
3. Testar edição.

Resultado esperado:
- a regra executa nos dois fluxos.

## Cenário E — before_delete
1. Criar regra `before_delete` com ação `reject`.
2. Tentar excluir um registro que satisfaça a condição.

Resultado esperado:
- registro permanece no banco;
- mensagem de bloqueio é exibida;
- não ocorre erro 500.

## Cenário F — prioridade e habilitação
1. Criar duas regras para o mesmo evento com prioridades diferentes.
2. Confirmar comportamento determinístico.
3. Desabilitar uma delas e repetir.

Resultado esperado:
- menor prioridade numérica executa primeiro;
- regra desabilitada é ignorada.

## Cenário G — regressão dos Designers
Confirmar abertura e salvamento de:
- Model Designer
- Form Designer
- CRUD Designer
- Business Rules Designer
- Dashboard Designer

Resultado esperado:
- nenhum Designer perde configuração existente;
- `estrutura_json` preserva chaves das demais capacidades.

## Cenário H — aplicação sem regras
Gerar uma aplicação sem configuração em `business_rules`.

Resultado esperado:
- CRUD continua com comportamento equivalente à GEN-051;
- nenhuma regra é executada;
- aplicação passa em `manage.py check`.

## Critério de promoção
Promover para `master` somente quando:
- suíte automatizada completa estiver aprovada;
- cenários A–H estiverem validados manualmente;
- não houver regressão em Form Designer, CRUD Designer ou geração;
- branch continuar baseada diretamente no baseline validado da GEN-051.
