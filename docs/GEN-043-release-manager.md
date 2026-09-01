# GEN-043 — Release Manager

## Objetivo

Transformar `VersaoGeracao` em uma entidade de ciclo de vida, permitindo que uma geração percorra estados formais até ser considerada release.

Fluxo alvo:

`DRAFT -> VALIDATING -> VALIDATED -> RELEASED`

## Princípios

1. A `master` da GEN-042 é o baseline.
2. O draft `numero=0` continua reservado para configurações em edição, como o Dashboard Builder.
3. Uma geração concluída deve produzir apenas uma versão numerada.
4. Uma versão só pode ser validada quando o Validation Center não possuir erros críticos.
5. Uma versão só pode ser publicada se estiver validada.
6. O Release Manager não executa deploy; deploy pertence às GENs posteriores.
7. Toda transição de estado deve ser explícita, previsível e coberta por testes.

## Escopo

### Ciclo de vida persistido

Adicionar a `VersaoGeracao`:

- `status`
- `changelog`
- `validado_em`
- `publicado_em`

Estados:

- `DRAFT`
- `VALIDATING`
- `VALIDATED`
- `RELEASED`

### Release Service

Responsabilidades:

- listar versões numeradas de um sistema;
- impedir publicação de drafts;
- validar transições de estado;
- integrar com o Validation Center;
- registrar changelog;
- marcar timestamps de validação/publicação;
- garantir apenas uma versão criada por processo de geração.

### Release Manager UI

Rota:

`/sistemas/<id>/releases/`

A tela deve mostrar:

- versão atual;
- status por versão;
- data de geração;
- changelog;
- resultado de validação;
- ações permitidas conforme o estado;
- indicação da release mais recente.

### Segurança

- somente o proprietário acessa e altera releases;
- draft `v0` não pode ser publicado;
- `RELEASED` é estado terminal nesta GEN;
- nenhuma ação altera a definição do sistema;
- nenhuma ação executa migration no sistema gerado;
- nenhuma ação executa deploy.

## Correção estrutural incluída

O fluxo atual registra uma versão em `GeradorService._registrar_versao()` e outra em `processar_geracao_ajax()` após criar o ZIP. A GEN-043 deve consolidar isso: o `GeradorService` cria a versão e o instalador completa essa mesma versão com o ZIP, sem gerar uma segunda versão.

## Testes

- estados default e transições válidas;
- draft v0 não pode ser publicado;
- versão não validada não pode ser publicada;
- validação com erro não promove versão;
- validação sem erro promove para VALIDATED;
- release registra timestamp e changelog;
- acesso somente pelo proprietário;
- geração não cria versão duplicada;
- regressões da GEN-042 continuam passando.

## Critério de aceite

1. migrations aplicadas com sucesso em cópia segura do banco local;
2. suíte completa passa;
3. geração produz uma única versão por execução;
4. Release Manager validado manualmente;
5. publicação de release respeita o Quality Gate;
6. confirmação manual antes de promover a GEN-043 para `master`.
