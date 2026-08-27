# GEN-035 — Dashboard Query Designer

## Objetivo
Transformar o Dashboard Builder em uma configuração de dados utilizável pelo gerador, sem exigir código.

## Configuração
Cada widget possui uma configuração normalizada com:
- operação: count, sum, avg, min, max;
- campo da operação;
- agrupamento;
- agrupamento por relacionamento;
- rótulo do relacionamento;
- campos da tabela;
- limite;
- ordenação.

## Compatibilidade
Widgets existentes continuam válidos. Configurações antigas recebem defaults durante a normalização.

## Escopo
A GEN-035 cobre o contrato e a experiência de configuração. A execução ORM e serialização pertencem ao runtime de dados.
