# GEN-0003 — Compilador de Especificação

## Objetivo

Transformar o `SystemSpec` canônico em artefatos Django sem que o pipeline de geração dependa diretamente do ORM.

## Fluxo

```text
Sistema ORM
    ↓
SpecificationBuilder
    ↓
SystemSpec
    ↓
CompilationPlan
    ↓
SpecificationCompiler
    ↓
CompiledFile
    ↓
ArtifactWriter
    ↓
Projeto Django
```

## Responsabilidades

### SpecificationCompiler

- recebe somente `SystemSpec`;
- resolve templates;
- constrói contextos derivados da especificação;
- produz `CompiledFile` em memória;
- garante que o conjunto produzido corresponde ao plano.

### ArtifactWriter

É a fronteira de filesystem. Recebe artefatos já compilados e grava somente dentro do diretório de saída permitido.

### GeradorService

Permanece como serviço de aplicação. Ele valida a especificação ORM, cria o `SystemSpec`, monta o plano e delega a compilação ao `SpecificationCompiler`.

## Compatibilidade

Os templates existentes ainda possuem alguns padrões históricos como `.all`. O compilador fornece pequenos adapters em memória para manter compatibilidade durante a migração. Esses adapters não possuem acesso ao banco.

## Critério de sucesso

A geração deverá produzir exatamente os caminhos previstos pelo `CompilationPlan`, e os testes deverão comprovar que relacionamentos entre módulos usam nomes técnicos canônicos.
