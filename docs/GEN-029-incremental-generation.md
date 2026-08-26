# GEN-029 — Geração Incremental

A especificação passa a ter uma representação canônica e uma impressão digital SHA-256.

## Objetivo
Detectar alterações antes de regenerar o projeto.

## Contrato
- `canonicalize_spec(spec)` produz snapshot determinístico.
- `spec_fingerprint(spec)` identifica a especificação.
- `diff_top_level(previous, current)` identifica seções alteradas.

## Regra de segurança
A detecção de mudança não autoriza apagar código automaticamente. Preservação de código existente e estratégia de merge continuam sendo responsabilidades explícitas do pipeline.
