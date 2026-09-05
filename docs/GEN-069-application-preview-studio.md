# GEN-069 — Application Preview Studio

## Objetivo

Permitir que o usuário veja **como a aplicação desenhada no DjangoForge deverá aparecer para quem vai utilizá-la**, antes de gerar o projeto Django.

Princípio de produto:

> O usuário configura o comportamento da aplicação nos Designers e usa o Preview Studio para verificar a experiência resultante.

O Application Preview Studio responde, em linguagem visual:

- como será o shell da aplicação;
- como o menu será apresentado;
- como listagens e formulários aparecerão;
- como dashboard e relatórios serão organizados;
- quais ações de workflow estarão disponíveis;
- como a experiência muda conforme o papel de negócio;
- como a interface se comporta em diferentes tamanhos de tela.

## Relação com o Application Blueprint

O Blueprint e o Preview Studio possuem responsabilidades diferentes e complementares.

```text
Designers especializados
        │
        ├── estrutura
        ├── interface
        ├── formulários
        ├── consultas
        ├── dashboard
        ├── relatórios
        ├── workflows
        └── permissões
                │
        ┌───────┴────────┐
        ▼                ▼
Application          Application
Blueprint            Preview Studio
        │                │
"O que existe?"     "Como ficará?"
```

O Blueprint continua sendo o mapa consolidado da aplicação. O Preview Studio é a representação visual da experiência projetada.

## Regra arquitetural central

O Preview Studio **não cria uma nova fonte de verdade**.

Não deve existir um contrato persistido paralelo como:

```text
estrutura_json["preview"]
```

O preview é derivado dos contratos existentes e das propriedades de interface já persistidas no `Sistema`.

A edição permanece nos Designers responsáveis.

```text
Preview Studio
     │
     ├── formulário ──────→ Form Designer
     ├── consulta ────────→ CRUD Designer
     ├── dashboard ───────→ Dashboard Designer
     ├── relatório ───────→ Report Designer
     ├── processo ────────→ Workflow Designer
     ├── acesso ──────────→ Permission Designer
     └── shell/aparência ─→ Interface Designer
```

## Fontes reais do preview

### Interface

O shell visual deve usar as propriedades já existentes no `Sistema`:

- `tipo_menu`;
- `interface_modo`;
- `interface_densidade`;
- `interface_nome`;
- `interface_cor_primaria`;
- `interface_cor_destaque`;
- `interface_breadcrumb`;
- `interface_busca`;
- `interface_menu_usuario`.

Nenhuma preferência visual específica do Preview deve ser salva nesses campos. Controles como Desktop/Tablet/Mobile são apenas estado transitório da sessão/tela de preview.

### Estrutura e páginas

O Preview Studio deve reutilizar os mesmos contratos e normalizadores consumidos pela geração:

- módulos, entidades e campos;
- `normalize_form_config`;
- `normalize_crud_config`;
- `normalize_dashboard_config`;
- contratos de relatórios;
- `normalize_workflow_config`;
- `normalize_rbac_config`.

A regra é importante: **o Preview não interpreta um contrato de maneira diferente do gerador**.

## O preview existente de geração não é o Preview Studio

O endpoint atual `gerar/<pk>/preview/` continua tendo outra responsabilidade.

Ele descreve uma geração já existente e retorna informações como:

- versão;
- estrutura serializada;
- arquivos gerados.

Esse endpoint funciona como inspeção técnica do artefato gerado. Ele **não representa visualmente a aplicação final** e não deve ser reutilizado como núcleo do Application Preview Studio.

Portanto:

```text
preview_geracao
    = inspeção técnica de artefato já gerado

Application Preview Studio
    = projeção visual antes da geração
```

## Arquitetura proposta

O Preview Studio deve possuir uma camada de projeção própria, somente leitura, construída sobre os contratos normalizados.

Representação inicial sugerida em memória:

```python
{
    "application": {
        "name": "Sistema de Contratos",
    },
    "shell": {
        "menu": "lateral",
        "mode": "automatico",
        "density": "confortavel",
        "primary_color": "#0d6efd",
        "accent_color": "#6f42c1",
        "breadcrumb": True,
        "search": True,
        "user_menu": True,
    },
    "navigation": [...],
    "pages": [...],
    "dashboard": {...},
    "roles": [...],
}
```

Essa representação é derivada e **não é persistida**.

## Fidelidade ao projeto gerado

O objetivo do Preview Studio é alta fidelidade de experiência, mas sem executar o projeto Django gerado.

A fidelidade deve vir do compartilhamento de contratos e normalizadores, não da duplicação manual de regras.

Regra:

> Se uma decisão visual ou comportamental puder ser determinada por um contrato existente, Preview e Gerador devem obter a resposta a partir do mesmo contrato normalizado.

Quando houver diferença inevitável entre preview e runtime real, a interface deve tratá-la como aproximação visual e nunca afirmar que executou comportamento real.

## Dados apresentados no preview

O Preview Studio não deve consultar nem criar registros reais das entidades da aplicação gerada.

Para representar listagens, formulários, dashboards e relatórios antes da geração, deve utilizar **dados demonstrativos efêmeros**.

Esses dados:

- não são persistidos;
- não alteram contratos;
- não representam dados reais do usuário;
- servem apenas para tornar a composição visual compreensível;
- devem ser determinísticos para o mesmo contrato sempre que possível.

Exemplo:

```text
Contrato 001
Contrato 002
Contrato 003
```

é aceitável como conteúdo demonstrativo de uma listagem, desde que visualmente identificado como preview.

## Navegação simulada

O usuário deve poder navegar dentro do Preview Studio entre experiências projetadas, sem executar as views do sistema gerado.

Exemplos:

- Dashboard;
- lista de Contratos;
- cadastro de Contrato;
- detalhes de Contrato;
- relatório configurado.

Essa navegação é uma simulação da experiência e não um runtime paralelo.

## Preview por papel

A seleção de papel pertence ao Preview Studio como estado transitório.

Exemplo:

```text
Visualizar como: Gestor
```

Ao selecionar um papel, a projeção pode usar o RBAC existente para decidir:

- quais informações aparecem na navegação;
- quais ações CRUD são visíveis;
- quais transições de workflow são apresentadas.

O Preview Studio **não inventa associação usuário → papel**. Ele simula diretamente um papel de negócio já existente no Permission Designer.

Se nenhum papel estiver selecionado, o Preview deve possuir uma visão neutra de design, explicitamente identificada como tal.

## Dispositivos

Desktop, Tablet e Mobile são modos de visualização transitórios.

```text
[ Desktop ] [ Tablet ] [ Mobile ]
```

Esses controles alteram somente o viewport do Preview Studio. Eles não criam configuração responsiva persistida nesta GEN.

Responsabilidades avançadas de composição pertencem à GEN-070 — Advanced Page Designer.

## Preview somente leitura

Na GEN-069 o Preview Studio é, por definição, **somente leitura**.

Não deve ser possível:

- arrastar campos para reorganizar formulários;
- alterar colunas de listagem;
- criar widgets;
- editar permissões;
- alterar workflow;
- mudar configurações persistidas diretamente no preview.

Cada contexto deve oferecer navegação para o Designer responsável.

## Limite entre GEN-069 e GEN-070

### GEN-069 — Application Preview Studio

Visualiza o resultado dos contratos existentes.

### GEN-070 — Advanced Page Designer

Será responsável por capacidades avançadas de composição de páginas que exigem configuração própria.

O Preview Studio não deve antecipar essa edição.

## Estratégia de implementação

O ciclo será incremental.

### GEN-069.1 — Contrato e arquitetura do Preview

- definir responsabilidade;
- definir fontes;
- separar preview visual de preview técnico de geração;
- estabelecer regra de não persistência;
- estabelecer dados demonstrativos e navegação simulada;
- estabelecer limites com GEN-070.

### GEN-069.2 — Shell da aplicação gerada

Projetar:

- nome da aplicação;
- menu lateral/superior;
- identidade visual;
- busca;
- breadcrumb;
- menu do usuário;
- densidade e modo visual.

### GEN-069.3 — Preview de listagens

Projetar CRUD/listagens usando `normalize_crud_config` e dados demonstrativos.

### GEN-069.4 — Preview de formulários

Projetar formulários, seções, largura e visibilidade usando `normalize_form_config`.

### GEN-069.5 — Preview de Dashboard e relatórios

Projetar dashboard e experiências de relatório a partir dos contratos existentes.

### GEN-069.6 — Preview de workflow e ações

Projetar estados e ações disponíveis na experiência do usuário.

### GEN-069.7 — Preview por papel / permissões

Aplicar RBAC sobre navegação e ações projetadas, sem inventar membership de usuários.

### GEN-069.8 — Desktop / Tablet / Mobile

Permitir troca de viewport sem persistência adicional.

### GEN-069.9 — Navegação Preview ↔ Designers

Conectar cada elemento do preview ao Designer que o controla.

### GEN-069.10 — Testes, regressão e freeze

Congelar uma baseline segura antes da GEN-070.

## Critérios de aceite da GEN-069.1

- Preview Studio e Blueprint possuem responsabilidades explicitamente distintas;
- Preview Studio é definido como projeção somente leitura;
- nenhuma nova fonte persistida de configuração é criada;
- fontes visuais e comportamentais são contratos existentes;
- o endpoint técnico `preview_geracao` não é confundido com o Preview Studio;
- dados demonstrativos são explicitamente efêmeros;
- seleção de papel não cria membership usuário → papel;
- Desktop/Tablet/Mobile é estado transitório;
- a GEN-069 não antecipa edição avançada da GEN-070;
- nenhuma migração de banco é necessária nesta etapa.

## Não objetivos da GEN-069.1

- construir imediatamente todas as páginas do preview;
- executar um projeto Django gerado dentro do DjangoForge;
- persistir dados de demonstração;
- editar contratos no preview;
- criar um navegador completo ou sandbox de runtime;
- antecipar o Advanced Page Designer.

## Gate

A GEN-069.1 é arquitetural/documental e parte da baseline segura da GEN-068.

```text
python manage.py check
python manage.py test
```

## Status

**GEN-069.1 — Contrato e arquitetura: IMPLEMENTED / AWAITING VALIDATION**
