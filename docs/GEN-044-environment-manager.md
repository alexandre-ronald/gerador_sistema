# GEN-044 — Environment Manager

## Objetivo

Adicionar gestão formal de ambientes ao ciclo de vida do DjangoForge, separando Development, Test, Staging e Production e vinculando releases publicadas aos ambientes sem executar deploy real nesta GEN.

## Princípios

1. A master validada da GEN-043 é o baseline.
2. Ambientes pertencem a um único Sistema.
3. Cada Sistema pode ter no máximo um ambiente por tipo.
4. Somente versões RELEASED podem ser associadas a ambientes.
5. A troca de release atual preserva histórico de promoções.
6. Esta GEN não executa SSH, Docker, migrations remotas ou deploy físico.
7. O modelo deve servir de contrato para a GEN-045 Runtime Agent.

## Tipos de ambiente

- DEVELOPMENT
- TEST
- STAGING
- PRODUCTION

## Ambiente

Campos mínimos:

- sistema
- tipo
- nome
- url_base
- ativo
- release_atual
- criado_em
- atualizado_em

## Histórico de promoção

Cada associação de release a um ambiente gera um registro imutável com:

- ambiente
- versão
- promovido_em
- observação

O Environment Manager altera apenas a referência lógica de release atual; deploy real fica fora do escopo.

## Regras

- draft v0 nunca pode ser promovido.
- versão DRAFT, VALIDATING ou VALIDATED não pode ser associada a ambiente.
- versão deve pertencer ao mesmo Sistema do ambiente.
- Production usa as mesmas regras básicas de Staging nesta GEN; políticas adicionais ficam para fases posteriores.
- excluir/desativar ambiente não deve excluir uma VersaoGeracao.

## Interface

Rota principal:

`/sistemas/<id>/environments/`

A tela deve apresentar:

- quatro ambientes padrão;
- URL e estado ativo/inativo;
- release atual;
- releases publicadas disponíveis;
- ação de promover uma release;
- histórico recente de promoções.

## Fora do escopo

- execução de deploy;
- credenciais e secrets;
- health check em tempo real;
- logs remotos;
- rollback executável;
- Runtime Agent;
- infraestrutura como código.

## Critérios de aceite

1. suite anterior continua passando;
2. novos testes da GEN-044 passam;
3. owner-only access;
4. quatro ambientes podem ser materializados de forma idempotente;
5. somente RELEASED pode ser promovida;
6. promoção cross-system é bloqueada;
7. histórico é preservado;
8. nenhuma operação toca arquivos do sistema gerado ou executa migrations remotas.
