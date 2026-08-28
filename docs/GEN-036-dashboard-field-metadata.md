# GEN-036 — Dashboard Field Metadata

## Objetivo
Evoluir o Dashboard Builder para conhecer os campos reais das entidades do Model Designer, eliminando configuração baseada apenas em texto livre.

## Escopo
- Expor metadata dos campos das entidades disponíveis.
- Exibir `verbose_name` e nome técnico.
- Identificar campos numéricos e `DecimalField`.
- Identificar `ForeignKey`, `OneToOneField` e `ManyToManyField`.
- Expor a entidade relacionada.
- Permitir seleção de campo, agrupamento e relacionamento no Builder.
- Manter a especificação do dashboard declarativa e compatível com o runtime.
- Garantir serialização segura de `Decimal`, `UUID`, datas e instâncias de `models.Model`.

## Contrato de metadata
Cada entidade possui `name`, `label`, `module` e `fields`.

Cada campo possui `name`, `label`, `type`, `nullable`, `relational`, `related_entity`, `related_label`, `numeric` e `decimal`.

## Critério de validação
O Dashboard Builder deve responder HTTP 200 e disponibilizar os campos cadastrados para uma entidade, incluindo seus rótulos (`verbose_name`) e tipos. O runtime deve continuar aceitando valores Decimal e UUID sem produzir erro de serialização JSON.

## Próxima GEN
A próxima evolução deve transformar a metadata em um mecanismo analítico completo: agregações, agrupamentos, consultas por relacionamentos e validação declarativa da configuração antes da geração.
