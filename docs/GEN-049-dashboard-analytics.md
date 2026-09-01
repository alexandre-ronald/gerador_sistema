# GEN-049 — Dashboard Analytics

Status: Draft 0.1

## Objetivo

Adicionar uma camada analítica sobre o Dashboard Data Engine da GEN-048 para permitir filtros estruturados, períodos temporais e comparação de períodos sem permitir SQL/ORM arbitrário e sem alterar o contrato visual do Dashboard Designer 2.0.

## Baseline

A GEN-049 nasce exclusivamente do baseline validado da GEN-048 (`b480d814bd6678b8b98b1d9ddf667ac46b37ca6b`).

Permanecem congelados:

- grid de 12 colunas;
- `x/y/w/h`;
- aparência do widget;
- Preview Mode;
- Runtime Agent;
- Environment/Release Manager;
- contrato seguro do Dashboard Data Engine.

## Princípios

1. Analytics é uma camada sobre o `DashboardQueryPlan`, não uma nova engine paralela.
2. Todo campo e operador recebido do Designer deve ser validado contra os metadados do sistema.
3. Nenhum lookup ORM com `__` será aceito diretamente do navegador.
4. Datas relativas devem ser resolvidas de forma determinística a partir de uma data de referência explícita.
5. Comparações devem reutilizar a mesma consulta base do widget, mudando apenas a janela temporal.
6. Erro analítico de um widget não deve derrubar o restante do dashboard.
7. A GEN-049 não cria migration.

## Escopo incluído

- `DashboardAnalyticsPlan`;
- filtros estruturados por campo;
- operadores seguros: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `contains`, `icontains`, `in`, `isnull`;
- validação do operador conforme tipo de campo;
- campo temporal explícito;
- períodos `all`, `today`, `current_week`, `current_month`, `current_year`, `last_7_days`, `last_30_days`, `last_90_days`, `custom`;
- intervalo customizado com início/fim;
- comparação `none`, `previous_period`, `previous_year`;
- resolução determinística de janelas de datas;
- aplicação posterior ao executor ORM da GEN-048;
- integração posterior ao dashboard gerado;
- testes de segurança e regressão.

## Fora do escopo

- SQL livre;
- fórmulas calculadas;
- joins arbitrários;
- filtros baseados em código Python;
- permissões em nível de linha;
- drill-down;
- cross-filter ao clicar em gráfico;
- fontes externas;
- cache distribuído;
- deploy;
- alterações no Runtime Agent;
- migrations.

## Contrato do widget

A configuração analítica ficará dentro de `config.analytics` e será retrocompatível. Widgets existentes sem esse bloco continuam executando como na GEN-048.

```json
{
  "type": "metric",
  "entity": "Pedido",
  "config": {
    "operation": "sum",
    "field": "valor_total",
    "analytics": {
      "date_field": "data_pedido",
      "period": "current_month",
      "custom_start": "",
      "custom_end": "",
      "compare": "previous_period",
      "filters": [
        {"field": "status", "operator": "eq", "value": "APROVADO"}
      ]
    }
  }
}
```

## Plano intermediário

```python
DashboardAnalyticsPlan(
    date_field="data_pedido",
    period="current_month",
    custom_start=None,
    custom_end=None,
    compare="previous_period",
    filters=(
        DashboardFilter(field="status", operator="eq", value="APROVADO"),
    ),
)
```

O plano analítico não contém `x/y/w/h`, título ou aparência.

## Campos temporais

Inicialmente serão aceitos como campo temporal:

- `DateField`;
- `DateTimeField`.

`period != all` ou `compare != none` exige `date_field` temporal válido.

## Períodos

### all

Não aplica janela temporal.

### today

Data de referência até a própria data de referência.

### current_week

Segunda-feira da semana da referência até a data de referência.

### current_month

Primeiro dia do mês até a data de referência.

### current_year

1º de janeiro até a data de referência.

### last_7_days / last_30_days / last_90_days

Janela inclusiva terminando na data de referência.

### custom

Exige `custom_start` e `custom_end`, em ISO `YYYY-MM-DD`, com início menor ou igual ao fim.

## Comparações

### none

Sem série/valor comparativo.

### previous_period

Usa uma janela imediatamente anterior com o mesmo número de dias da janela principal.

### previous_year

Desloca início e fim em um ano calendário. Datas de 29 de fevereiro devem ser tratadas deterministicamente.

Comparação não é permitida quando o período é `all`.

## Filtros

Formato:

```json
{"field": "status", "operator": "eq", "value": "APROVADO"}
```

Regras:

- `field` deve existir na entidade do widget;
- nomes com `__` são rejeitados;
- `operator` deve pertencer à whitelist;
- `in` exige lista/tupla;
- `isnull` exige booleano;
- `contains`/`icontains` somente em campos textuais;
- operadores de ordem (`gt/gte/lt/lte`) somente em campos numéricos, data/hora ou tipos simples ordenáveis definidos por teste;
- filtros vazios são ignorados somente quando explicitamente normalizados; configuração malformada gera erro de domínio.

## Erros de domínio

Códigos iniciais:

- `invalid_analytics`
- `invalid_filter`
- `invalid_filter_field`
- `invalid_filter_operator`
- `invalid_filter_value`
- `invalid_date_field`
- `invalid_period`
- `invalid_custom_period`
- `invalid_comparison`

## Arquitetura

```text
Dashboard Designer
      ↓
widget.config
      ↓
DashboardDataEngine.compile()
      ↓
DashboardQueryPlan
      +
DashboardAnalyticsEngine.compile()
      ↓
DashboardAnalyticsPlan
      ↓
DashboardDataEngine.execute(..., analytics_plan)
      ↓
resultado atual + comparação
```

## Blocos de implementação

### GEN-049.1 — Analytics Plan

- dataclasses de filtro e analytics;
- validação de filtros;
- validação de campo temporal;
- períodos/comparação;
- resolução das janelas de datas;
- testes unitários.

### GEN-049.2 — Executor analítico

- converter filtros seguros para kwargs ORM internos;
- aplicar janela temporal;
- executar período atual;
- executar comparação sem duplicar regras do Query Plan;
- saída serializável.

### GEN-049.3 — Designer

- controles de período;
- campo temporal;
- comparação;
- editor de filtros;
- metadados compatíveis com entidade selecionada;
- retrocompatibilidade com widgets GEN-047/048.

### GEN-049.4 — Runtime gerado

- gerar execução equivalente no sistema produzido;
- mensagens de erro por widget;
- preservar payload atual para widgets sem analytics.

### GEN-049.5 — Regressão e validação

- suíte completa;
- KPI com período e comparação;
- gráfico agrupado filtrado;
- tabela filtrada;
- cenário sem analytics idêntico à GEN-048;
- validação manual.

## Critérios de aceitação

1. Widget legado sem `analytics` mantém comportamento GEN-048.
2. Filtro por campo inexistente é rejeitado antes do ORM.
3. Lookup arbitrário é rejeitado.
4. Operador incompatível com tipo é rejeitado.
5. Período relativo gera janela determinística.
6. Período customizado inválido é rejeitado.
7. Comparação `previous_period` gera janela anterior de mesmo tamanho.
8. Comparação `previous_year` é determinística inclusive em ano bissexto.
9. Analytics não altera `x/y/w/h` ou `appearance`.
10. Runtime gerado mantém isolamento de erros por widget.
11. Nenhuma migration.
12. Todos os testes anteriores continuam passando.

## Próximo passo

Implementar apenas a GEN-049.1 e validar antes de tocar no executor ORM ou no Dashboard Designer.
