# GEN-030 — Dashboard Builder

## Objetivo
Permitir que o usuário componha dashboards sem escrever código, usando widgets configuráveis e um grid de 12 colunas.

## Contrato
- dashboard: `enabled`, `title`, `layout`, `refresh_seconds`, `widgets`
- widgets: `id`, `type`, `title`, `entity`, posição `x/y`, tamanho `w/h` e `config`
- tipos iniciais: metric, table, bar, line, area, pie, donut

## Regras
1. O Dashboard Builder trabalha sobre entidades já definidas pelo Model Designer.
2. O widget não altera a estrutura de dados.
3. A especificação é normalizada antes da geração.
4. Layout e tema são independentes dos dados.
5. A geração incremental deve identificar alterações no dashboard pelo snapshot canônico.

## Resultado esperado
O usuário monta o dashboard visualmente; o pipeline recebe uma especificação declarativa única e gera a implementação correspondente.
