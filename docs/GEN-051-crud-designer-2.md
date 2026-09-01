# GEN-051 — CRUD Designer 2.0

Status: Draft 0.1
Baseline: GEN-050 — Form Designer
Branch: `gen-051-crud-designer-2`

## 1. Objetivo

Evoluir a geração CRUD do DjangoForge para que a experiência de listagem e operação de cada entidade possa ser configurada visualmente, mantendo o Model Designer como fonte estrutural e o Form Designer como fonte da experiência de criação/edição.

O CRUD Designer 2.0 controla principalmente a experiência de **listar, localizar, ordenar e agir sobre registros**.

## 2. Princípios

1. Model Designer continua sendo a fonte da estrutura de entidades e campos.
2. Form Designer continua controlando criação e edição.
3. CRUD Designer controla listagem, consulta e ações CRUD.
4. Ausência de configuração CRUD deve preservar integralmente o comportamento legado.
5. Configuração persistida no draft `VersaoGeracao.numero=0`, em `estrutura_json`.
6. Nenhum SQL, Python, JavaScript ou template arbitrário será aceito como configuração.
7. Consultas geradas devem usar ORM Django e campos previamente validados.
8. GEN-047 a GEN-050 permanecem compatíveis e sem regressão.
9. A configuração visual deve ser materializada no sistema Django gerado, não depender do DjangoForge em runtime.

## 3. Contrato proposto

```json
{
  "cruds": {
    "Pedido": {
      "title": "Pedidos",
      "page_size": 25,
      "default_order": "-data_criacao",
      "columns": [
        {
          "field": "numero",
          "label": "Número",
          "order": 0,
          "visible": true,
          "sortable": true
        }
      ],
      "search": {
        "enabled": true,
        "fields": ["numero", "descricao"],
        "placeholder": "Pesquisar pedidos"
      },
      "filters": [
        {
          "field": "status",
          "label": "Status",
          "type": "select",
          "order": 0
        }
      ],
      "actions": {
        "create": true,
        "view": true,
        "edit": true,
        "delete": true
      }
    }
  }
}
```

O contrato definitivo poderá ser refinado durante GEN-051.1, mantendo compatibilidade com esta intenção funcional.

## 4. Escopo incluído

### 4.1 Entidade

- seleção da entidade;
- título da listagem;
- tamanho da página;
- ordenação padrão segura.

### 4.2 Colunas

- selecionar campos exibidos;
- ordenar colunas;
- label visual customizado;
- visível/oculta;
- permitir ordenação por coluna quando compatível;
- Preview da tabela no Designer.

### 4.3 Busca

- habilitar/desabilitar busca;
- selecionar campos pesquisáveis compatíveis;
- placeholder customizado;
- pesquisa textual via ORM Django;
- nenhum lookup arbitrário fornecido pelo usuário.

### 4.4 Filtros

Primeiro conjunto seguro:

- texto;
- select/choices;
- booleano;
- data;
- relacionamento simples quando suportado de forma segura.

Cada filtro terá campo, label, tipo e ordem.

### 4.5 Ordenação

- ordenação padrão;
- colunas explicitamente marcadas como ordenáveis;
- parâmetro de ordenação validado contra allowlist gerada;
- sem `order_by()` arbitrário vindo diretamente da URL.

### 4.6 Paginação

Valores inicialmente suportados:

- 10;
- 25;
- 50;
- 100.

Valor padrão: 25 quando existir configuração CRUD. Sem configuração, manter comportamento legado.

### 4.7 Ações

Configuração visual das ações padrão:

- Novo;
- Visualizar;
- Editar;
- Excluir.

As ações apenas habilitam/desabilitam capacidades CRUD já conhecidas. GEN-051 não introduz execução arbitrária de ações customizadas.

### 4.8 Sistema gerado

A configuração deve produzir código Django convencional:

- views baseadas em ORM;
- templates Bootstrap;
- busca segura;
- filtros seguros;
- ordenação segura;
- paginação;
- ações configuradas;
- integração com os formulários gerados pela GEN-050.

## 5. Normalização e compatibilidade

Quando uma entidade não possuir configuração em `cruds`:

- usar listagem legada;
- preservar colunas legadas;
- preservar paginação e ações legadas;
- não alterar URLs existentes;
- não exigir configuração do Form Designer.

Quando novos campos forem adicionados ao Model Designer:

- a configuração existente não deve ser destruída;
- novos campos podem aparecer como disponíveis no Designer;
- não devem ser automaticamente inseridos em uma listagem customizada já salva, salvo decisão explícita de normalização futura.

Campos removidos devem ser ignorados com segurança na normalização.

## 6. Validação de segurança

Rejeitar configurações com:

- entidade inexistente;
- campo inexistente em atualização direta;
- colunas duplicadas;
- campos de busca incompatíveis;
- filtros incompatíveis;
- tipo de filtro não permitido;
- `page_size` fora da allowlist;
- ordenação padrão fora dos campos permitidos;
- valores não booleanos para flags;
- lookups ORM arbitrários;
- caminhos com `__` fornecidos diretamente pelo usuário;
- Python, SQL, JavaScript ou expressões de template arbitrárias.

## 7. Interface do CRUD Designer

Estrutura inicial:

- seletor de entidade;
- toolbar com Preview e Salvar;
- painel de configuração geral;
- painel de colunas;
- painel de busca;
- painel de filtros;
- painel de ações;
- Preview central da listagem.

A experiência visual deve seguir o padrão profissional já estabelecido pelo Dashboard Designer e Form Designer, inclusive notificações não bloqueantes de salvamento.

## 8. Fora do escopo

- ações customizadas com código;
- bulk actions avançadas;
- exportação Excel/PDF/CSV;
- importação;
- filtros compostos AND/OR configuráveis;
- query builder livre;
- joins arbitrários;
- inline forms;
- master-detail avançado;
- regras condicionais de ação;
- permissões por ação/campo;
- workflow;
- regras de negócio;
- autocomplete remoto avançado;
- customização completa da página Detail;
- templates arbitrários.

Esses itens pertencem a GENs futuras, especialmente Business Rules, Workflow, RBAC e Integration Center.

## 9. Fases

### GEN-051.1 — CRUD Contract

- normalizador;
- defaults;
- validações;
- compatibilidade com metadados atuais;
- testes unitários do contrato.

### GEN-051.2 — CRUD Designer UI

- rota e backend;
- seleção de entidade;
- configuração de colunas;
- busca;
- filtros;
- ordenação;
- paginação;
- ações;
- Preview;
- persistência no draft;
- testes da UI e endpoints.

### GEN-051.3 — Generated CRUD Runtime

- integrar contrato ao `GeradorService`;
- gerar views ORM seguras;
- gerar listagem configurada;
- busca;
- filtros;
- ordenação;
- paginação;
- ações;
- fallback legado;
- testes dos artefatos realmente gerados.

### GEN-051.4 — Regression & Validation

- `manage.py check`;
- testes GEN-051;
- suíte completa;
- geração real de sistema;
- validação manual no navegador;
- revisão GEN-050 → GEN-051;
- promoção somente após aprovação.

## 10. Critérios de aceite

GEN-051 estará concluída quando:

1. Uma entidade puder ter sua listagem configurada visualmente.
2. Colunas, labels e ordem forem refletidos no sistema gerado.
3. Busca operar somente sobre campos permitidos.
4. Filtros forem seguros e funcionais.
5. Ordenação via URL for validada por allowlist.
6. Paginação configurada for aplicada.
7. Ações CRUD padrão respeitarem a configuração.
8. Form Designer continuar funcionando para create/update.
9. Entidades sem configuração CRUD mantiverem o comportamento legado.
10. Testes novos e regressão completa passarem.
11. O CRUD gerado for validado manualmente no navegador.

## 11. Restrições de implementação

- Não requer migration do DjangoForge nesta GEN: configuração permanece no JSON do draft.
- Não alterar `master` durante desenvolvimento.
- Não alterar contratos validados das GEN-047, GEN-048, GEN-049 e GEN-050 sem necessidade comprovada.
- Não executar migration ou operações destrutivas no banco local como parte da implementação.
