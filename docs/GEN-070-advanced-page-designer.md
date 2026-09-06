# GEN-070 — Advanced Page Designer

## Objetivo

Permitir que o usuário monte **páginas e experiências de negócio além do CRUD padrão**, combinando informações, componentes, ações, navegação e regras já conhecidas pelo DjangoForge.

Princípio de produto:

> O usuário desenha a experiência da aplicação. O DjangoForge transforma essa intenção em contratos normalizados, preview fiel e runtime Django coerente.

A GEN-070 deve ampliar a composição sem criar um segundo sistema de configuração nem um runtime paralelo.

## Relação com as GENs anteriores

A GEN-067 definiu o modelo de acesso orientado a papéis e capacidades.

A GEN-068 consolidou a estrutura no Application Blueprint.

A GEN-069 projetou visualmente a experiência resultante dos contratos existentes e definiu que composição avançada pertence à GEN-070.

Portanto:

```text
Designers existentes
      │
      ├── CRUD
      ├── Form
      ├── Dashboard
      ├── Reports
      ├── Workflow
      ├── Permissions
      └── Interface
             │
             ▼
Advanced Page Designer
             │
             ├── composição de página
             ├── experiências não-CRUD
             ├── reutilização de contratos
             └── novas ligações declarativas
             │
      ┌──────┴──────────┐
      ▼                 ▼
Preview Studio       Runtime gerado
```

## Decisão de escopo: Runtime Contract Enforcement

A necessidade de **Runtime Contract Enforcement** passa a integrar formalmente a GEN-070.

Não será tratada, neste momento, como uma GEN separada.

Motivo:

> Uma página avançada só é válida se o runtime respeitar os mesmos contratos usados pelo Designer e pelo Preview.

Isso inclui, quando aplicável:

- permissões CRUD;
- acesso a páginas;
- acesso a relatórios;
- ações e transições de workflow;
- visibilidade de navegação;
- ações disponíveis na interface;
- comportamento fail-closed para configurações inválidas ou não autorizadas.

## Regra arquitetural central

O Advanced Page Designer **não substitui** os Designers especializados.

Ele deve compor e orquestrar contratos existentes sempre que possível.

Exemplos:

```text
Form Designer
    define como um formulário funciona

Advanced Page Designer
    decide onde e em qual experiência esse formulário aparece
```

```text
Report Designer
    define o relatório

Advanced Page Designer
    pode incluir acesso, resumo ou navegação para esse relatório
```

```text
Workflow Designer
    define estados e transições

Advanced Page Designer
    pode apresentar ações de workflow, mas não redefinir o processo
```

## Fonte de verdade

A GEN-070 deve possuir contrato declarativo persistido para páginas avançadas, mas esse contrato não pode duplicar configurações já pertencentes a outros Designers.

A definição exata do schema será fechada na GEN-070.1 antes da implementação funcional.

Diretriz inicial:

```text
advanced_pages
    ├── identidade da página
    ├── rota/navegação declarativa
    ├── layout
    ├── componentes
    ├── bindings/referências
    ├── condições de visibilidade
    └── ações/referências a contratos existentes
```

O contrato deve usar IDs estáveis e referências explícitas.

## O que é uma página avançada

Uma página avançada é uma experiência composta que não pode ser descrita adequadamente apenas como:

- listagem CRUD;
- formulário CRUD;
- dashboard isolado;
- relatório isolado.

Exemplos de experiências que a GEN-070 deve permitir representar:

- página de detalhe operacional com resumo + ações + histórico;
- central de acompanhamento de um processo;
- página mestre/detalhe;
- página com indicadores, tabela e formulário contextual;
- página de atendimento com blocos de informações relacionadas;
- workspace de uma entidade ou processo;
- página inicial contextual por papel;
- composição de cards, tabelas, textos, ações e blocos de dados.

## Componentes

A primeira versão deve priorizar componentes declarativos de alto valor e baixa ambiguidade.

Categorias previstas:

### Conteúdo

- título;
- texto;
- separador;
- alerta/informação contextual.

### Dados

- card/KPI;
- tabela/listagem;
- detalhe de registro;
- campos/resumo;
- bloco de relatório;
- bloco de dashboard quando compatível.

### Interação

- botão/ação;
- link/navegação;
- formulário contextual;
- ação de workflow.

A existência de um componente visual não autoriza duplicar a lógica de seu Designer de origem.

## Layout

A composição deve reutilizar o conceito de grade de 12 colunas já adotado no projeto.

Requisitos iniciais:

- linhas e colunas;
- largura de 1 a 12 colunas;
- ordenação visual;
- mover componentes;
- redimensionar componentes;
- reposicionamento determinístico quando não houver espaço na linha;
- comportamento responsivo previsível.

Uma alteração de tamanho não pode causar sobreposição silenciosa.

## Binding de dados

Componentes devem obter dados por referências declarativas e normalizadas.

A GEN-070 não deve incentivar SQL ou Python inserido pelo usuário.

Bindings podem apontar para capacidades já existentes, por exemplo:

- entidade;
- campos;
- configuração CRUD;
- relatório;
- consulta/dashboard;
- contexto de registro;
- workflow.

Bindings mais avançados só entram no escopo quando puderem ser representados declarativamente e validados.

## Contexto da página

Uma página pode possuir contexto, por exemplo:

```text
Página: Detalhe do Contrato
Contexto: um registro de Contrato
```

ou

```text
Página: Central de Contratos
Contexto: coleção de Contratos
```

Esse contexto deve ser explícito no contrato para que Designer, Preview e Runtime interpretem a página da mesma maneira.

## Ações

Ações devem preferir referências a capacidades existentes.

Exemplos:

- criar registro;
- abrir detalhe;
- editar;
- excluir;
- executar transição de workflow;
- abrir relatório;
- navegar para outra página declarada.

A página não deve inventar uma permissão independente para uma ação que já possui política no Permission Designer.

## Runtime Contract Enforcement

O runtime gerado deve aplicar os contratos que o Preview já consegue projetar.

### CRUD

Rotas e ações geradas devem respeitar capacidades `list`, `view`, `create`, `update` e `delete`.

### Workflow

Uma transição só pode ser executada quando o papel/autorização permitir e o estado atual for compatível.

### Reports

Relatórios protegidos por RBAC devem ser bloqueados também por acesso direto à rota, não apenas ocultados na navegação.

### Navegação

Itens indisponíveis ao papel atual não devem aparecer como opções navegáveis.

### Páginas avançadas

A página e seus componentes devem respeitar as permissões das capacidades que referenciam.

### Fail-closed

Quando houver política ativa e a configuração estiver inválida, adulterada ou não conceder autorização, o runtime deve negar acesso em vez de ampliar permissões implicitamente.

## Preview

O Application Preview Studio continua sendo projeção somente leitura.

A GEN-070 deve integrá-lo ao novo Designer para fechar o ciclo:

```text
Advanced Page Designer
        ↓
Preview Studio
        ↓
voltar ao Designer no mesmo contexto
```

O Preview não deve editar o contrato diretamente.

## Responsividade

A GEN-069 simulou Desktop/Tablet/Mobile sem persistência de regras responsivas.

A GEN-070 pode introduzir comportamento responsivo persistido apenas quando necessário à composição avançada.

Primeira regra:

> O layout base de 12 colunas deve degradar de forma previsível antes de permitir customizações responsivas complexas.

Customizações por breakpoint devem entrar incrementalmente, não como requisito inicial obrigatório.

## Escopo incluído

- contrato de páginas avançadas;
- Page Designer visual;
- layout declarativo em 12 colunas;
- componentes iniciais de conteúdo, dados e interação;
- contexto de página;
- bindings declarativos;
- ações referenciando contratos existentes;
- navegação para páginas avançadas;
- integração Preview ↔ Advanced Page Designer;
- geração/runtime das páginas suportadas;
- enforcement de RBAC, workflow, reports e ações aplicáveis;
- testes de equivalência Designer/Preview/Runtime;
- regressão e freeze.

## Fora do escopo inicial

- editor livre de HTML/CSS/JavaScript;
- execução arbitrária de Python;
- construtor genérico de qualquer aplicação sem restrições;
- substituição do Form, CRUD, Report, Workflow, Dashboard ou Permission Designer;
- banco de dados paralelo para o Designer;
- duplicação de regras de permissão;
- regras responsivas extremamente granulares na primeira etapa;
- runtime independente do projeto Django gerado.

## Estratégia de implementação

### GEN-070.1 — Contrato, domínio e governança

- oficializar escopo;
- definir conceito de página, contexto, componente, layout, binding e ação;
- definir schema canônico e IDs estáveis;
- definir normalizador e validador;
- definir regras de compatibilidade com Designers existentes;
- manter documentação e changelog de escopo.

### GEN-070.2 — Page Designer Shell

- criar acesso no Workspace;
- listar páginas;
- criar, duplicar, renomear e remover páginas;
- selecionar contexto da página;
- definir rota e navegação;
- sem ainda antecipar componentes complexos.

### GEN-070.3 — Layout Engine da página

- grade de 12 colunas;
- adicionar, mover e redimensionar blocos;
- evitar sobreposição;
- reposicionar blocos de forma determinística;
- persistir layout no contrato canônico.

### GEN-070.4 — Componentes e bindings

- componentes iniciais;
- seleção de fontes declarativas;
- binding de entidade/campo/registro/coleção;
- reutilização de CRUD, Form, Dashboard e Report quando aplicável.

### GEN-070.5 — Ações e experiências de processo

- botões e navegação;
- ações CRUD referenciadas;
- ações de workflow;
- páginas de detalhe/processo;
- condições de visibilidade derivadas de contexto e autorização.

### GEN-070.6 — Runtime Contract Enforcement

- enforcement CRUD no runtime gerado;
- enforcement de workflow;
- enforcement de relatórios;
- enforcement de páginas e componentes;
- filtragem de navegação;
- comportamento fail-closed.

### GEN-070.7 — Runtime de páginas avançadas

- geração de rotas;
- views/contexto;
- templates/componentes;
- navegação integrada;
- uso dos mesmos contratos normalizados do Designer e Preview.

### GEN-070.8 — Preview Studio integrado

- projetar páginas avançadas;
- Desktop/Tablet/Mobile;
- papel simulado;
- Preview ↔ Advanced Page Designer com preservação de contexto.

### GEN-070.9 — Equivalência e testes

- Designer → contrato;
- contrato → Preview;
- contrato → runtime;
- testes de autorização;
- testes de layout;
- testes de navegação;
- testes de não persistência de estado transitório.

### GEN-070.10 — Regressão e freeze

- `python manage.py check`;
- suíte completa;
- validação visual;
- baseline segura;
- atualização do roadmap e status final.

## Critérios de aceite da GEN-070.1

- Advanced Page Designer possui responsabilidade distinta dos Designers existentes;
- Runtime Contract Enforcement está formalmente incluído na GEN-070;
- composição não duplica configurações de CRUD/Form/Report/Workflow/RBAC;
- página, contexto, componente, layout, binding e ação possuem definições claras;
- a fonte de verdade continua sendo contrato declarativo persistido;
- Preview e Runtime devem compartilhar normalização/validação sempre que aplicável;
- mudanças futuras de escopo devem atualizar este arquivo e `docs/PROJECT_ROADMAP.md`;
- nenhuma implementação estrutural deve preceder a definição do schema canônico da GEN-070.1.

## Governança de mudanças de escopo

Este documento é parte do contrato de planejamento da GEN-070.

Qualquer mudança material deve acrescentar uma entrada ao changelog abaixo contendo:

- data;
- decisão;
- motivo;
- impacto em fases, arquitetura ou compatibilidade.

Não se deve apagar silenciosamente decisões anteriores; quando uma decisão for substituída, a nova entrada deve indicar explicitamente a mudança.

## Changelog de escopo

### 2026-09-06 — escopo inicial oficializado

**Decisão:** manter a GEN-070 como **Advanced Page Designer**.

**Motivo:** esse era o próximo marco planejado após o Application Preview Studio e a GEN-069 já reservava explicitamente a composição avançada para esta GEN.

**Impacto:** páginas e experiências além do CRUD são o eixo principal desta GEN.

### 2026-09-06 — Runtime Contract Enforcement incorporado

**Decisão:** incorporar **Runtime Contract Enforcement** à GEN-070 em vez de abrir uma GEN separada.

**Motivo:** a composição avançada precisa respeitar no runtime os mesmos contratos de autorização e comportamento usados pelo Designer e pelo Preview.

**Impacto:** a GEN-070 inclui enforcement de CRUD, workflow, relatórios, navegação e páginas avançadas, além de testes de equivalência Preview × Runtime.

## Gate inicial

A GEN-070 parte da baseline final da GEN-069:

```text
574fa04baf9fdce67a145a79e647b81900f4b9dd
```

Branch:

```text
gen-070-advanced-page-designer
```

Antes de avançar da GEN-070.1 para implementação funcional:

```text
python manage.py check
python manage.py test
```

## Status

**GEN-070.1 — Contrato, domínio e governança: DOCUMENTED / AWAITING IMPLEMENTATION**
