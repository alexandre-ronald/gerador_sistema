# GEN-034 — Dashboard Query Designer

## Objetivo

Tornar a configuração de dados do Dashboard compreensível para o usuário, sem exigir conhecimento dos nomes internos `operation`, `field` e `group_by`.

## Contrato

Cada widget poderá declarar uma definição de dados normalizada:

- `source`: entidade de origem;
- `operation`: `count`, `sum`, `avg`, `min`, `max`;
- `field`: campo usado pela operação quando aplicável;
- `group_by`: campo usado para agrupamento;
- `fields`: campos exibidos em tabelas;
- `limit`: limite de registros/categorias;
- `order`: ordenação.

## Princípio

A interface do Builder deve trabalhar com rótulos amigáveis e o pipeline deve traduzir a configuração para uma especificação determinística. Templates não devem conter regras de negócio nem SQL.

## Compatibilidade

Widgets criados nas GEN anteriores continuam válidos. Campos ausentes recebem defaults compatíveis.

## Próxima implementação

A GEN-034 deverá levar este contrato para a interface do Dashboard Builder e para a normalização centralizada, preservando o runtime validado da GEN-033.
