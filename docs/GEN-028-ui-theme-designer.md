# GEN-028 — UI / Theme Designer

O tema é tratado como configuração declarativa, separada do HTML.

## Contrato
- menu: `lateral` ou `superior`
- density: `compact`, `comfortable`, `spacious`
- dark_mode: `system`, `light`, `dark`
- identidade: nome, cor primária e cor de destaque
- breadcrumbs, busca e menu do usuário

## Regra
O tema não altera o domínio nem o contrato do Model Designer. A geração deve consumir uma única configuração normalizada.
