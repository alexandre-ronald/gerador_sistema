# GEN-039 — Baseline de não regressão

## Regra principal

A GEN-039 parte exatamente do commit estável da GEN-038:

- Branch de origem: `gen-038-dashboard-grid-stabilization`
- Commit-base: `25cdde443d5af061f5c257089726a62e7d79fa1e`
- Branch da GEN-039: `gen-039-regression-safe-baseline`

A GEN-039 deve ser tratada como evolução incremental da GEN-038. Nenhum comportamento validado pela GEN-038 deve ser removido ou alterado sem requisito explícito.

## Protocolo obrigatório

1. Executar a suíte completa de testes antes de qualquer alteração.
2. Considerar todos os testes existentes como contrato de regressão.
3. Implementar somente o escopo da GEN-039.
4. Adicionar testes para todo comportamento novo.
5. Executar novamente a suíte completa.
6. Se um teste anterior falhar, tratar primeiro como regressão.
7. Não alterar um teste existente apenas para fazê-lo passar quando o comportamento anterior ainda for válido.
8. Só concluir a GEN-039 com a suíte completa verde.
9. O commit final da GEN-039 será a única base autorizada para a GEN-040.

## Contrato preservado da GEN-038

A GEN-039 herda integralmente, entre outros, os seguintes comportamentos já testados:

- rota real do Dashboard Builder;
- renderização do canvas;
- presença da paleta de widgets;
- salvamento do dashboard em versão de rascunho `0`;
- rejeição de entidade desconhecida;
- grid de 12 colunas;
- posicionamento de três widgets de largura 4 na primeira linha;
- deslocamento para a próxima linha quando não há espaço suficiente;
- reflow após alteração de largura sem sobreposição;
- persistência de largura e altura dos widgets;
- normalização de tipos, dimensões e configuração do widget.

## Critério de saída

A GEN-039 somente estará concluída quando:

```text
GEN-038 estável
      ↓
GEN-039 incremental
      ↓
testes anteriores continuam passando
      ↓
testes novos passam
      ↓
suíte completa verde
      ↓
commit estável
      ↓
GEN-040
```

Qualquer falha de teste existente bloqueia a conclusão até que a causa da regressão seja corrigida ou que exista uma mudança de requisito explicitamente documentada.
