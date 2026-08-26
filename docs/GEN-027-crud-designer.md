# GEN-027 — CRUD Designer

## Regra
O CRUD Designer configura o comportamento da entidade sem duplicar regras no template.

## Contrato
- `enabled`
- `actions`: list, detail, create, update, delete
- `search_fields`
- `filter_fields`
- `ordering`
- `page_size` entre 1 e 200
- `confirm_delete`
- `bulk_actions`

## Princípio
A UI coleta a especificação; `builder_contracts.py` normaliza; o gerador consome o contrato normalizado.

## Compatibilidade
Entidades existentes continuam usando CRUD completo por padrão. Nenhuma opção avançada do Model Designer é removida.
