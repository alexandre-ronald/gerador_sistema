# GEN-068 — Application Blueprint

## Objetivo

Transformar os contratos já desenhados no DjangoForge em uma **visão consolidada, compreensível e verificável da aplicação antes da geração**.

Princípio de produto:

> O usuário não precisa conhecer a estrutura interna do projeto Django para entender o sistema que está construindo.

O Application Blueprint responde, em linguagem de produto e negócio:

- o que existe na aplicação;
- como as partes se relacionam;
- quais experiências serão entregues;
- quais processos existem;
- quem pode fazer o quê;
- quais partes ainda estão incompletas ou inconsistentes.

## Regra arquitetural central

O Blueprint **não cria uma nova fonte de verdade**.

```text
Contratos declarativos existentes
        │
        ├── entidades e campos
        ├── formulários
        ├── CRUD/páginas
        ├── workflows
        ├── dashboards
        ├── navegação
        ├── RBAC
        └── demais capacidades declaradas
                 ↓
        Application Blueprint
                 ↓
       projeção consolidada
```

Ele lê os contratos existentes, normaliza uma representação de leitura e produz uma projeção. Alterações continuam sendo feitas nos Designers responsáveis por cada contrato.

## Roadmap

- GEN-068.1 — Contrato e arquitetura do Blueprint
- GEN-068.2 — Inventário consolidado da aplicação
- GEN-068.3 — Mapa de informações e relacionamentos
- GEN-068.4 — Mapa de experiências e páginas
- GEN-068.5 — Processos e responsabilidades
- GEN-068.6 — Cobertura e prontidão da aplicação
- GEN-068.7 — Navegação entre Blueprint e Designers
- GEN-068.8 — Testes, regressão e freeze

## GEN-068.1 — Contrato e arquitetura

### O Blueprint é uma projeção

A primeira decisão do ciclo é separar claramente **contrato** de **projeção**.

O estado persistido continua pertencendo aos contratos que já existem no draft da aplicação. O Blueprint não terá um `blueprint` editável paralelo dentro de `estrutura_json`.

Uma representação derivada pode existir em memória para facilitar renderização e validação:

```python
{
    "application": {...},
    "inventory": {...},
    "information": [...],
    "experiences": [...],
    "processes": [...],
    "access": {...},
    "readiness": {...},
}
```

Essa estrutura é **resultado de leitura**, não um novo contrato persistido.

### Fontes

A implementação deve descobrir e consumir somente contratos realmente existentes no projeto. Nenhuma seção pode inventar configuração ausente apenas para completar visualmente o Blueprint.

Quando uma capacidade não estiver configurada, a projeção deve representar explicitamente essa ausência.

### Responsabilidade de edição

```text
Blueprint
   │
   ├── mostra Entidades ───────→ Designer responsável
   ├── mostra Formulários ─────→ Designer responsável
   ├── mostra Processos ───────→ Workflow Designer
   ├── mostra Acesso ──────────→ Permission Designer
   └── mostra demais áreas ────→ Designer correspondente
```

O Blueprint pode orientar e navegar. Ele não deve duplicar os editores especializados.

### Linguagem

A interface deve priorizar termos como:

- Informações da aplicação
- Experiências
- Processos
- Papéis e responsabilidades
- Navegação
- Prontidão

Termos internos como model, view, URL pattern, Django Group, permission codename e detalhes de geração permanecem fora da experiência principal.

### Determinismo

Para o mesmo conjunto de contratos normalizados, o Blueprint deve produzir a mesma representação. Isso permitirá posteriormente:

- comparação entre versões;
- análise de impacto;
- validação arquitetural;
- regeneração segura;
- explicação por IA.

Essas capacidades pertencem a ciclos posteriores e não devem ser antecipadas como persistência na GEN-068.

## Critérios de aceite da GEN-068.1

- existe uma definição explícita do Application Blueprint;
- está documentado que ele é uma projeção e não uma segunda fonte de verdade;
- as fontes devem ser contratos existentes e descobertos no repositório;
- ausência de configuração deve permanecer ausência, sem inferência silenciosa;
- edição continua pertencendo aos Designers especializados;
- linguagem da experiência é orientada ao produto/negócio;
- a representação derivada deve ser determinística;
- nenhuma alteração de schema ou migração é necessária nesta etapa.

## Não objetivos da GEN-068.1

- construir toda a interface final;
- persistir um novo contrato `blueprint`;
- editar entidades, workflows ou permissões dentro do Blueprint;
- gerar código novo a partir de informações que não existam nos contratos atuais;
- antecipar o Application Preview Studio da GEN-069.

## Gate

A GEN-068.1 é arquitetural e documental. As próximas subetapas devem preservar a regressão da baseline GEN-067:

```text
python manage.py check
python manage.py test
```
