# GEN-057.5 — Layout & UX Foundation

## Objetivo

Reorganizar a experiência visual do DjangoForge e modernizar o layout padrão das aplicações geradas, reduzindo carga cognitiva, deixando o fluxo de trabalho mais didático e corrigindo inconsistências de navegação ativa.

A GEN-057.5 parte da branch RC da GEN-057 (`gen-057-deployment-center`) e deve ser concluída antes da evolução para GEN-058.

## Problemas observados

### 1. DjangoForge — excesso de opções em "Meus Sistemas"

A tela atual expõe diretamente, dentro de cada sistema, praticamente todas as ferramentas de Design, Build e Run. Embora exista agrupamento por etapa, o usuário precisa conhecer previamente o propósito de cada ferramenta e a ordem recomendada de uso.

Consequências:

- excesso de informação por card;
- baixa hierarquia visual entre ações principais e secundárias;
- dificuldade para entender a sequência de construção do sistema;
- mistura de ações de projeto, geração, publicação, operação e monitoramento;
- aumento da curva de aprendizado.

### 2. Aplicação gerada — layout funcional, porém ainda pouco moderno

O template gerado já possui sidebar, topbar, tema claro/escuro e componentes Bootstrap, mas ainda precisa de uma linguagem visual mais consistente e contemporânea para uso corporativo.

### 3. Aplicação gerada — múltiplos itens de navegação marcados como ativos

O template atual marca um item como ativo usando principalmente:

`request.resolver_match.app_name == item.app_name`

Quando várias transações pertencem ao mesmo app Django, todos os itens daquele app recebem a classe `active` ao mesmo tempo.

O estado ativo deve identificar a transação/rota atual, não somente o app.

## Princípios

1. **Menos opções visíveis por contexto** — mostrar primeiro o que o usuário precisa para a etapa atual.
2. **Progressive disclosure** — ferramentas avançadas continuam acessíveis, mas não competem visualmente com ações principais.
3. **Fluxo didático** — a interface deve explicar Design → Build → Run → Govern.
4. **Uma ação ativa por navegação** — o menu deve refletir exatamente a rota/transação atual.
5. **Consistência entre Forge e Runtime** — ambos devem compartilhar princípios visuais, sem precisar compartilhar o mesmo HTML.
6. **Responsividade real** — desktop, tablet e mobile.
7. **Acessibilidade** — foco visível, contraste, labels e navegação por teclado.
8. **Compatibilidade** — projetos antigos continuam abrindo e gerando.
9. **Sem alteração funcional silenciosa** — esta GEN não deve mudar regras de negócio de designers, releases ou deployment.

## Escopo

### A. DjangoForge Workspace

#### A1. Nova organização de "Meus Sistemas"

Cada sistema deixa de apresentar uma grade extensa de links equivalentes.

O card deve priorizar:

- nome e descrição;
- status/resumo técnico;
- etapa atual/recomendada;
- ação principal `Abrir Workspace`;
- ação rápida `Gerar/Compilar` quando aplicável;
- menu secundário para ações administrativas.

As ferramentas completas ficam dentro do Workspace do sistema.

#### A2. Workspace didático por áreas

O Workspace deve organizar capacidades em quatro áreas conceituais:

**Design**
- Model Designer
- Form Designer
- CRUD Designer
- Business Rules
- Workflow Designer
- Permission Designer
- API Designer
- Integration Center
- Dashboard Designer

**Build**
- Validation Center
- Release Manager
- Gerar aplicação

**Run**
- Environment Manager
- Deployment Center
- Health & Monitoring

**Govern**
- visão futura para observabilidade, backup, auditoria e recursos das próximas GENs

Cada ferramenta deve ter:

- nome amigável;
- descrição curta do que faz;
- indicação de quando usar;
- estado visual quando disponível;
- ação clara para abrir.

#### A3. Navegação persistente do Workspace

Criar uma navegação própria do sistema selecionado, evitando retornar a `Meus Sistemas` para trocar de ferramenta.

A navegação pode usar sidebar ou rail responsivo, contendo as áreas Design, Build, Run e Govern.

#### A4. Hierarquia de ações

Definir três níveis:

- primária: próxima ação recomendada;
- secundária: ações comuns;
- terciária: configurações, download, exclusão e administração.

Ação destrutiva nunca deve competir visualmente com a ação principal.

### B. Design System do DjangoForge

Criar tokens e padrões reutilizáveis para:

- cores semânticas;
- tipografia;
- espaçamento;
- radius;
- shadows;
- cards;
- badges;
- botões;
- estados vazio/loading/error/success;
- cabeçalhos de página;
- navegação;
- tabelas;
- formulários;
- modais.

Evitar CSS duplicado por página sempre que possível.

### C. Layout padrão da aplicação gerada

#### C1. Shell moderno

Evoluir o shell gerado com:

- sidebar visualmente mais leve;
- melhor hierarquia entre módulo e transação;
- topbar limpa;
- breadcrumb/contexto de página;
- conteúdo com largura e espaçamento consistentes;
- estados hover/active/focus claros;
- modo mobile com drawer;
- tema dark coerente;
- avatar/menu do usuário;
- componentes com aparência corporativa contemporânea.

#### C2. Navegação por módulo e transação

A navegação deve distinguir:

- módulo/grupo;
- transação/item;
- rota atual.

A condição de `active` não pode depender somente de `app_name`.

Contrato recomendado para cada item de navegação:

```python
{
    "label": "Clientes",
    "app_name": "cadastros",
    "url_name": "cliente_list",
    "active_url_names": [
        "cliente_list",
        "cliente_create",
        "cliente_update",
        "cliente_detail",
    ],
}
```

Regra de ativação:

```text
resolver_match.url_name ∈ item.active_url_names
```

Se `active_url_names` não existir, usar `url_name` como fallback.

Assim uma tela de inclusão/edição continua destacando a transação correta sem marcar todas as transações do app.

#### C3. Ícones por transação

O gerador deve permitir ou inferir ícones de navegação, evitando o mesmo ícone genérico para todos os itens.

#### C4. Cabeçalho contextual de página

Templates CRUD devem suportar:

- título;
- subtítulo opcional;
- breadcrumb;
- ação primária;
- ações secundárias.

#### C5. Modernização CRUD

Atualizar visual padrão de:

- listagens;
- filtros;
- formulários;
- detalhes;
- exclusão;
- paginação;
- empty states;
- feedback de sucesso/erro.

Sem alterar contratos de URL, models ou permissões.

## Fora do escopo

- novo framework frontend;
- React/Vue;
- substituição do Bootstrap;
- mudanças em regras de negócio;
- novo Dashboard Engine;
- Logs & Observability;
- Backup Manager;
- AI Copilot;
- redesign de todos os designers internos em uma única etapa;
- temas totalmente customizáveis por cliente nesta primeira versão.

## Fases

### GEN-057.5.1 — UX Architecture

- inventário visual do DjangoForge atual;
- mapa de navegação;
- definição do novo Workspace;
- hierarquia de ações;
- contrato de navegação ativa do sistema gerado;
- design tokens iniciais;
- testes de contrato sem redesign massivo.

### GEN-057.5.2 — DjangoForge Workspace

- simplificar `Meus Sistemas`;
- implementar `Abrir Workspace`;
- criar navegação didática Design / Build / Run / Govern;
- adicionar descrições e contexto das ferramentas;
- manter todas as rotas existentes;
- testes de permissão, links e regressão.

### GEN-057.5.3 — Generated App Navigation

- corrigir active state por transação;
- adicionar contrato `active_url_names`;
- garantir apenas um item principal ativo;
- preservar destaque em create/update/detail da mesma transação;
- testes de geração e renderização.

### GEN-057.5.4 — Generated App Visual Refresh

- modernizar base layout;
- sidebar/topbar;
- cards/tabelas/forms;
- cabeçalho contextual;
- responsividade;
- dark mode;
- acessibilidade básica;
- atualizar templates gerados e testes de estabilidade.

### GEN-057.5.5 — Regression & Manual Validation

- `python manage.py check`;
- testes específicos da GEN;
- suíte completa `python manage.py test sistema`;
- gerar aplicação de referência;
- validar sidebar e topbar;
- validar item ativo em list/create/update/detail;
- validar desktop/tablet/mobile;
- validar tema claro/escuro;
- validar DjangoForge `Meus Sistemas` e Workspace;
- somente então congelar a GEN-057.5.

## Critérios de aceite

1. `Meus Sistemas` não expõe todas as ferramentas como ações de mesmo peso.
2. Existe uma entrada clara `Abrir Workspace` para cada sistema.
3. Workspace explica visualmente Design, Build, Run e Govern.
4. Cada ferramenta possui descrição curta e propósito compreensível.
5. Todas as rotas existentes continuam acessíveis.
6. Nenhum recurso validado de GEN anterior é removido.
7. No sistema gerado, abrir uma transação marca somente a navegação correspondente.
8. Create, update e detail podem manter ativa a transação pai correta.
9. O sistema gerado continua suportando menu lateral e superior.
10. Layout gerado é responsivo e coerente em light/dark mode.
11. Templates CRUD recebem modernização sem alterar contratos funcionais.
12. Testes de estabilidade de geração continuam passando.
13. A suíte anterior do DjangoForge permanece verde.
14. A validação manual é concluída antes de qualquer promoção.

## Estratégia de baseline

A GEN-057.5 nasce da RC `gen-057-deployment-center` porque a GEN-057 ainda possui somente a validação Docker real pendente por limitação do host atual.

A nova branch é:

`gen-057-5-layout-ux`

A branch GEN-057 RC deve permanecer preservada e sem novas mudanças funcionais.

## Próximo roadmap após conclusão

- GEN-058 — Logs & Observability
- GEN-059 — Backup Manager
- GEN-060 — AI Copilot

A GEN-057.5 torna-se a fundação visual para essas próximas capacidades.