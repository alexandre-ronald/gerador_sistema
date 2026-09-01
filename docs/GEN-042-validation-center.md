# GEN-042 — Validation Center

## Objetivo

Transformar as validações já existentes do DjangoForge em uma capacidade de produto visível, rastreável e orientada a releases.

O Validation Center será a porta de qualidade entre uma definição de sistema e uma versão considerada apta para release.

## Princípios

1. A `master` validada pela GEN-041 é o baseline e não deve ser alterada durante o desenvolvimento desta GEN.
2. Nenhuma validação existente deve ser removida ou enfraquecida.
3. A primeira entrega reutiliza os validadores atuais antes de criar novos mecanismos.
4. Falhas críticas impedem o status `VALIDATED`.
5. Warnings são apresentados separadamente e não devem ser confundidos com sucesso.
6. Cada execução deve produzir um resultado estruturado que futuramente poderá ser persistido como manifesto de qualidade.

## Escopo da GEN-042

### 1. Validation Service

Criar uma camada de serviço que consolide checks em categorias independentes:

- Definition / Models
- Relationships
- Generation
- Python syntax
- Django templates
- Base/navigation contracts
- Dependencies
- Django system check
- Dashboard

Cada check deve retornar, no mínimo:

- `key`
- `label`
- `status`: `success`, `warning`, `error`, `pending`
- `summary`
- `details`

O resultado consolidado deve informar:

- sistema
- versão analisada
- status geral
- total de checks
- sucessos
- warnings
- erros
- timestamp da execução

### 2. Validation Center UI

Adicionar uma tela por sistema:

`/sistemas/<id>/validation-center/`

A tela deverá apresentar:

- status geral do sistema;
- versão/draft analisado;
- cards de resumo;
- lista dos checks;
- detalhes de warnings e erros;
- indicação clara de apto/não apto para release.

### 3. Execução segura

A validação não pode:

- executar migrations;
- modificar `db.sqlite3`;
- alterar models;
- alterar a definição do sistema;
- promover automaticamente uma versão;
- apagar artefatos gerados.

### 4. Testes

Adicionar regressões para:

- somente o proprietário acessar o Validation Center;
- resultado consolidado possuir contrato estável;
- sistema válido produzir checks estruturados;
- erro crítico tornar o resultado geral inválido;
- warnings permanecerem distintos de errors;
- dashboard fazer parte do relatório;
- tela renderizar sem alterar o sistema;
- suíte anterior continuar passando.

## Fora do escopo

Ficam para GENs posteriores:

- persistência histórica de cada execução;
- estados formais DRAFT/VALIDATING/VALIDATED/RELEASED;
- comparação entre releases;
- ambientes DEV/STAGING/PRODUCTION;
- Runtime Agent;
- deploy e rollback.

## Critério de aceite

A GEN-042 somente poderá ser promovida para `master` quando:

1. todos os testes anteriores continuarem passando;
2. os novos testes da GEN-042 passarem;
3. a tela Validation Center for validada manualmente;
4. nenhuma migration ou alteração de banco for necessária nesta primeira etapa;
5. o usuário confirmar que o fluxo está correto.
