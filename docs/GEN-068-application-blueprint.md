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

## Roadmap concluído

- GEN-068.1 — Contrato e arquitetura do Blueprint ✅
- GEN-068.2 — Inventário consolidado da aplicação ✅
- GEN-068.3 — Mapa de informações e relacionamentos ✅
- GEN-068.4 — Mapa de experiências e páginas ✅
- GEN-068.5 — Processos e responsabilidades ✅
- GEN-068.6 — Cobertura e prontidão da aplicação ✅
- GEN-068.7 — Navegação entre Blueprint e Designers ✅
- GEN-068.8 — Testes, regressão e freeze ✅

## GEN-068.1 — Contrato e arquitetura

### O Blueprint é uma projeção

A primeira decisão do ciclo é separar claramente **contrato** de **projeção**.

O estado persistido continua pertencendo aos contratos que já existem no draft da aplicação. O Blueprint não possui um `blueprint` editável paralelo dentro de `estrutura_json`.

Uma representação derivada existe somente em memória para facilitar renderização e leitura:

```python
{
    "application": {...},
    "inventory": {...},
    "information": [...],
    "relationships": [...],
    "experiences": [...],
    "dashboard": {...},
    "processes": [...],
    "responsibilities": [...],
    "readiness": {...},
}
```

Essa estrutura é **resultado de leitura**, não um novo contrato persistido.

### Fontes

A implementação consome contratos realmente existentes no projeto. Nenhuma seção inventa configuração ausente apenas para completar visualmente o Blueprint.

Quando uma capacidade não está configurada, a projeção representa explicitamente essa ausência ou a sinaliza na prontidão.

### Responsabilidade de edição

```text
Blueprint
   │
   ├── mostra Estrutura ───────→ Model Designer
   ├── mostra Formulários ─────→ Form Designer
   ├── mostra Consultas ───────→ CRUD Designer
   ├── mostra Relatórios ──────→ Report Designer
   ├── mostra Dashboard ───────→ Dashboard Designer
   ├── mostra Processos ───────→ Workflow Designer
   ├── mostra Responsabilidades → Permission Designer
   └── mostra Prontidão ───────→ Validation Center
```

O Blueprint orienta e navega. Ele não duplica os editores especializados.

### Linguagem

A interface prioriza termos de produto e negócio: Informações da aplicação, Experiências e páginas, Processos de negócio, Papéis e responsabilidades e Cobertura e prontidão.

Termos internos como model, view, URL pattern, Django Group, permission codename e detalhes de geração permanecem fora da experiência principal.

### Determinismo

Para o mesmo conjunto de contratos normalizados, o Blueprint produz a mesma representação. Módulos, entidades e campos possuem ordenação explícita na projeção.

Isso prepara ciclos posteriores para comparação entre versões, análise de impacto, validação arquitetural, regeneração segura e explicação por IA sem antecipar essas capacidades na GEN-068.

## Resultado funcional congelado

A GEN-068 entrega:

1. inventário consolidado de áreas, informações, campos, relacionamentos, processos e papéis;
2. mapa de informações e relacionamentos em linguagem de negócio;
3. projeção de experiências derivadas de Form Designer, CRUD Designer, Report Designer e Dashboard Designer;
4. projeção dos processos reais definidos no Workflow Designer;
5. projeção de papéis, capacidades e ações de processo definidas no Permission Designer;
6. cobertura e prontidão baseada nos contratos explicitamente revisados, distinguindo revisão de correção necessária;
7. navegação direta para cada Designer especializado e Validation Center;
8. iconografia dos atalhos consistente com o Workspace;
9. comportamento responsivo dos cards, textos, badges, processos e responsabilidades;
10. Blueprint somente leitura, sem novo schema, migração ou fonte de verdade.

## Limites congelados

Ficam deliberadamente fora da GEN-068:

- edição de contratos dentro do Blueprint;
- persistência de `estrutura_json["blueprint"]`;
- preview visual/interativo da aplicação final;
- simulação Desktop/Tablet/Mobile;
- visualização por papel como usuário final;
- Advanced Page Designer;
- Component Designer;
- comparação/evolução entre versões;
- análise de impacto e regeneração segura.

O preview visual/interativo pertence à **GEN-069 — Application Preview Studio**.

## Regressão e baseline

Antes do freeze, o Workspace foi comparado com a baseline segura da GEN-067. Foram restaurados comportamentos e conteúdos que haviam sido perdidos durante a integração inicial do Blueprint, incluindo:

- badge condicional de Docker;
- descrições completas dos Designers;
- ação **Gerar aplicação** na etapa Build;
- nota de evolução futura em Govern.

As adições legítimas da GEN-068 permanecem: botão **Ver Blueprint** no hero e **Application Blueprint** como primeira ferramenta da etapa Design.

## Gate final validado

Validação do usuário em **2026-09-05**: todos os testes verdes e validação visual aprovada.

```text
python manage.py check
python manage.py test sistema.test_workspace_navigation
python manage.py test sistema.test_application_blueprint
python manage.py test
```

Também foram validados visualmente:

- contenção e responsividade dos cards;
- altura dos blocos de processo;
- Blueprint e Workspace após restauração da baseline;
- atalhos e iconografia de navegação.

## Status

**GEN-068 — Application Blueprint: FROZEN / SAFE BASELINE**

Próximo ciclo: **GEN-069 — Application Preview Studio**.
