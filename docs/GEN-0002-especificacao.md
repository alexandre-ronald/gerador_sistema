# GEN-0002 — Motor de Especificação

## Objetivo

Transformar a especificação armazenada pelo editor Django em um objeto canônico, independente do ORM, que possa ser consumido por validação, planejamento e, nas próximas fases, pelo compilador do gerador.

## Entregas

- `sistema/specification.py`: modelo canônico da especificação.
- `sistema/specification_plan.py`: plano determinístico dos artefatos que serão gerados.
- `GeradorService.especificacao()`: acesso à especificação canônica.
- `GeradorService.plano_compilacao()`: inspeção do plano sem escrever arquivos.
- `sistema/test_gen0002.py`: testes de conversão, fingerprint e plano.

## Modelo

```text
SystemSpec
  └── ModuleSpec
        └── EntitySpec
              └── FieldSpec
```

Cada nível possui nomes humanos e nomes técnicos normalizados.

## Fingerprint

A especificação é serializada em JSON canônico e recebe um SHA-256. O fingerprint permite, em fases futuras, identificar exatamente qual especificação produziu uma geração, implementar cache e auditoria e detectar alterações entre versões.

## Plano de compilação

O `CompilationPlan` lista os artefatos esperados sem criar arquivos. Isso separa a decisão **o que gerar** da execução **como gerar**.

## Compatibilidade

A geração existente continua baseada nos modelos ORM nesta fase. O GEN-0002 introduz a representação canônica sem substituir o gerador atual, reduzindo o risco de regressão. A migração para o compilador baseado em `SystemSpec` será feita na próxima etapa.
