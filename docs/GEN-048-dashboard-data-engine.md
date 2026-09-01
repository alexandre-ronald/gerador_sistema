# GEN-048 — Dashboard Data Engine

Status: Draft 0.1

## Objetivo

Criar uma camada explícita, validável e reutilizável que transforme a configuração persistida de cada widget do Dashboard Designer em um plano de consulta seguro. A GEN-048 prepara a execução de dados reais sem alterar o grid, o Preview Mode ou o Runtime Agent.

## Baseline

A GEN-048 nasce exclusivamente do baseline validado da GEN-047 (`077a28f4c6cf3e14a5ed4731251ed9a2618019a5`). O contrato visual e de layout da GEN-047 permanece congelado.

## Princípios

1. O Dashboard Designer descreve **o que** o widget precisa; o Data Engine decide **como** consultar.
2. Configuração do cliente nunca vira lookup ORM arbitrário sem validação contra metadados do sistema.
3. `x/y/w/h` e `appearance` não pertencem ao Data Engine e não serão reinterpretados.
4. A engine deve ser independente da view e testável sem navegador.
5. Erros de configuração devem produzir erros de domínio previsíveis, não exceções ORM expostas ao usuário.
6. A GEN-048 não adiciona migration nem altera o SQLite.

## Escopo incluído

- contrato `DashboardQueryPlan` para um widget;
- resolução da entidade configurada;
- validação de campos contra `Campo`/`Entidade`;
- operações `count`, `sum`, `avg`, `min`, `max`;
- agrupamento simples por campo;
- agrupamento por relacionamento previamente descrito pelo Designer;
- seleção de campos para widget `table`;
- ordenação validada;
- limite validado;
- distinção entre campos numéricos e não numéricos;
- erros estruturados de configuração;
- testes unitários do compilador de consultas;
- integração posterior com o contexto do dashboard gerado.

## Fora do escopo

- novas fontes de dados externas;
- SQL livre;
- joins arbitrários;
- filtros globais de dashboard;
- drill-down;
- expressões/fórmulas calculadas;
- cache distribuído;
- permissões em nível de linha;
- deploy;
- mudanças no Runtime Agent;
- migrations.

## Entrada

A entrada é um widget já normalizado pelo contrato do Dashboard Builder. Exemplo:

```json
{
  "id": "widget-total",
  "type": "metric",
  "entity": "Pedido",
  "config": {
    "operation": "sum",
    "field": "valor_total",
    "group_by": "status",
    "group_by_related": "",
    "related_label": "__str__",
    "fields": [],
    "limit": 100,
    "ordering": "-valor_total"
  }
}
```

## Saída: DashboardQueryPlan

A engine não deve espalhar regras ORM pela aplicação. Ela compila a configuração para um plano intermediário:

```python
DashboardQueryPlan(
    entity="Pedido",
    operation="sum",
    value_field="valor_total",
    group_by="status",
    group_by_related="",
    related_label="__str__",
    table_fields=(),
    ordering="-valor_total",
    limit=100,
)
```

O plano é o contrato entre Designer e executor.

## Regras de validação

### Entidade

A entidade deve pertencer ao `Sistema` atual. Entidades desconhecidas são rejeitadas.

### Operações

Operações permitidas:

- `count`
- `sum`
- `avg`
- `min`
- `max`

`count` pode operar sobre `id`. `sum` e `avg` exigem campo numérico. `min` e `max` inicialmente aceitam campos numéricos e campos ordenáveis simples, conforme evolução coberta por testes.

### Campos

Todo campo recebido do JSON deve existir nos metadados da entidade. A engine nunca deve aceitar um lookup arbitrário fornecido pelo navegador.

### Relacionamentos

`group_by_related` só pode apontar para campo relacional conhecido. O label relacionado deve ser resolvido a partir do contrato conhecido; a GEN-048 não permitirá caminhos relacionais arbitrários enviados pelo cliente.

### Tabela

`fields` deve ser uma lista de campos válidos. Se estiver vazia, o executor poderá aplicar um conjunto padrão determinístico em etapa posterior.

### Ordenação

Aceita `campo` ou `-campo`, desde que o campo pertença à entidade ou ao conjunto explicitamente permitido pelo plano. Lookups com `__` enviados diretamente pelo cliente são rejeitados, salvo caminhos relacionais produzidos internamente pela engine.

### Limite

O limite deve ser inteiro entre 1 e 500. O contrato normalizado continuará usando 100 como padrão.

## Erros de domínio

Criar exceção própria, por exemplo `DashboardDataError`, com código estável e mensagem legível. Códigos iniciais:

- `entity_not_found`
- `field_not_found`
- `invalid_operation`
- `numeric_field_required`
- `invalid_grouping`
- `invalid_related_grouping`
- `invalid_table_fields`
- `invalid_ordering`
- `invalid_limit`

## Arquitetura proposta

```text
Dashboard Designer
      ↓ JSON normalizado
builder_contracts.py
      ↓
DashboardDataEngine.compile(...)
      ↓
DashboardQueryPlan
      ↓
DashboardDataEngine.execute(...)
      ↓
resultado normalizado do widget
```

A primeira implementação deve separar `compile` de `execute`. Assim conseguimos validar completamente o contrato antes de acoplar consultas reais.

## Blocos de implementação

### GEN-048.1 — Query Plan + validação

- `DashboardQueryPlan`;
- `DashboardDataError`;
- compilação de entidade, operação, campo, grouping, fields, ordering e limit;
- testes unitários.

### GEN-048.2 — Executor ORM

- `count`;
- agregações;
- agrupamentos;
- tabelas;
- saída serializável.

### GEN-048.3 — Relacionamentos

- agrupamento relacional seguro;
- label relacionado;
- testes de FK e configurações inválidas.

### GEN-048.4 — Integração

- integrar resultados ao runtime/dashboard gerado sem alterar o contrato visual da GEN-047;
- estados de erro previsíveis por widget.

### GEN-048.5 — Regressão

- suíte GEN-041 → GEN-047 intacta;
- testes específicos GEN-048;
- validação manual com metric/table/chart.

## Critérios de aceitação

1. Configuração válida gera plano determinístico.
2. Entidade inexistente é rejeitada antes do ORM.
3. Campo inexistente é rejeitado antes do ORM.
4. `sum`/`avg` em campo não numérico é rejeitado.
5. Ordenação arbitrária/lookup injetado é rejeitado.
6. Limite fora da faixa é rejeitado.
7. Tabela aceita apenas campos conhecidos.
8. Agrupamento simples produz plano válido.
9. Agrupamento relacional aceita somente relacionamento conhecido.
10. Execução produz estruturas serializáveis para metric/table/chart.
11. Nenhuma alteração em `x/y/w/h` ou `appearance`.
12. Nenhuma migration.
13. Todos os testes anteriores continuam passando.

## Estratégia de regressão

A GEN-048 deve acrescentar testes; não substituir testes do Dashboard Designer por asserts mais fracos. Em especial permanecem protegidos:

- grid de 12 colunas;
- reflow;
- drag-and-drop;
- duplicação;
- presets;
- Preview Mode;
- aparência;
- coordenadas exatas no dashboard gerado;
- metadados analíticos do Designer.

## Próximo passo

Implementar somente a GEN-048.1: Query Plan, erros de domínio e compilador validado por testes. Não integrar consultas ORM reais até esse bloco estar aprovado.