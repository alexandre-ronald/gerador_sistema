# GEN-0003 — Compilador de Projetos Django

## Objetivo

Transformar um `SystemSpec` canônico em um projeto Django executável, usando um plano determinístico de artefatos e templates, sem depender dos objetos ORM durante a compilação.

## Pipeline

```text
SystemSpec
    ↓
CompilationPlan
    ↓
SpecificationCompiler
    ↓
CompiledFile
    ↓
ArtifactWriter / filesystem
    ↓
GeneratedProjectValidator
    ↓
Exportação ZIP
```

## Responsabilidades

### SpecificationCompiler

- recebe somente `SystemSpec`;
- resolve templates;
- constrói contextos derivados da especificação;
- produz `CompiledFile` em memória;
- garante que os caminhos produzidos correspondem exatamente ao `CompilationPlan`.

### ArtifactWriter

É a fronteira de filesystem. Nenhum artefato pode escapar do diretório de saída autorizado.

### GeneratedProjectValidator

Executa uma validação estrutural antes da exportação:

- verifica todos os artefatos planejados;
- analisa sintaticamente todos os arquivos Python gerados;
- verifica nomes técnicos em `INSTALLED_APPS`;
- verifica imports técnicos nos `include()` das URLs.

### GeradorService

Permanece como serviço de aplicação. Valida a especificação ORM, cria o `SystemSpec`, monta o plano, compila, grava e só persiste `caminho_geracao` depois que a árvore passou pela validação estrutural.

## Nomes técnicos

Nomes humanos são usados para apresentação. Identificadores Python usam exclusivamente nomes técnicos canônicos:

```text
Gestão de Pessoas
        ↓
gestao_de_pessoas
```

Isso vale para diretórios, imports, `INSTALLED_APPS`, classes e referências entre módulos.

## Critérios de aceite

Uma geração GEN-0003 só deve ser considerada concluída quando:

1. o plano e os artefatos produzidos forem idênticos em caminhos;
2. os arquivos Python forem sintaticamente válidos;
3. o projeto passar pela validação estrutural;
4. o diretório de geração for persistido somente após a validação;
5. a exportação ZIP consumir uma árvore previamente validada.

## Fora do escopo

- Custom User completo;
- geração completa de APIs REST;
- migrações previamente materializadas no projeto gerado;
- execução de testes funcionais do sistema gerado.

Esses itens serão tratados em fases posteriores.
