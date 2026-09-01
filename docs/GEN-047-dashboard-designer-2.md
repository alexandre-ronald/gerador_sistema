# GEN-047 — Dashboard Designer 2.0

## Objetivo

Evoluir o Dashboard Builder validado na GEN-041 para um designer de dashboards mais produtivo e profissional, preservando integralmente o contrato de grid de 12 colunas e a fidelidade entre o canvas e o sistema gerado.

## Princípios

1. A `master` validada da GEN-046 é o baseline.
2. Não reescrever o algoritmo de grid estabilizado na GEN-041.
3. `x`, `y`, `w` e `h` continuam sendo a fonte canônica do layout.
4. Nenhum widget pode ultrapassar as 12 colunas ou sobrepor outro após normalização/reflow.
5. O designer deve ganhar produtividade sem antecipar o Data Engine da GEN-048.
6. A configuração persistida deve continuar retrocompatível com dashboards existentes.
7. Nenhuma migration é necessária nesta GEN: o contrato permanece no JSON do draft.

## Escopo

### Incluído

- toolbar do designer;
- duplicar widget;
- mover widget uma célula por vez via controles explícitos;
- resize por controles explícitos mantendo reflow;
- presets de tamanho;
- propriedades visuais por widget;
- alinhamento e organização automática;
- preview mode no próprio builder;
- identificação clara de widget selecionado;
- resumo de posição/tamanho;
- testes de regressão do contrato de dashboard.

### Não incluído

- novas fontes de dados;
- joins/queries avançadas;
- filtros analíticos globais;
- drill-down;
- deploy;
- mudanças no Runtime Agent;
- alteração do banco do DjangoForge.

## Contrato visual por widget

A configuração do widget passa a aceitar, dentro de `config`, metadados visuais opcionais:

```json
{
  "appearance": {
    "variant": "default",
    "show_header": true,
    "show_border": true,
    "compact": false
  }
}
```

Valores ausentes devem receber defaults, mantendo compatibilidade com dashboards anteriores.

## Presets

- Pequeno: 3x2
- Médio: 4x3
- Largo: 6x3
- Linha inteira: 12x3
- Alto: 4x5

Todos passam pelo mesmo `normalizeWidget` e `reflowWidgets` já validados.

## Organização

O comando `Organizar` deve percorrer os widgets na ordem atual e posicioná-los no primeiro espaço livre, sem sobreposição, respeitando largura e altura.

## Preview

O modo Preview oculta a paleta/propriedades e remove affordances de edição sem alterar a configuração persistida. Sair do Preview retorna ao mesmo estado do designer.

## Critérios de aceite

1. Dashboards existentes continuam abrindo.
2. Adicionar widget continua usando o primeiro espaço livre.
3. Duplicar cria novo ID e posiciona a cópia em espaço livre.
4. Resize continua provocando reflow quando necessário.
5. Movimento não produz sobreposição.
6. Organizar compacta o canvas de forma determinística.
7. Preview não altera dados.
8. Salvar mantém `x/y/w/h` e propriedades visuais.
9. Dashboard gerado continua fiel às coordenadas do canvas.
10. Toda a suíte anterior continua passando.
