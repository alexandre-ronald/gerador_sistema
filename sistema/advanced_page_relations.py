"""GEN-071.1 — contrato seguro para bindings relacionais de páginas avançadas.

A relação é declarativa e usa apenas metadados já conhecidos pelo domínio. Nesta
primeira fase, o único transporte suportado é o registro atual da página para um
campo relacional da entidade-alvo:

    Contrato.fornecedor = page_context.pk

Nenhum SQL, lookup Django arbitrário ou código do usuário é aceito.
"""
from copy import deepcopy

from .advanced_pages import AdvancedPageContractError


RELATION_SOURCE_PAGE_CONTEXT = "page_context"
RELATION_SOURCE_FIELDS = ("pk",)
RELATIONAL_FIELD_TYPES = ("ForeignKey", "OneToOneField", "ManyToManyField")


def normalize_relation_config(raw, *, page_id, component_id):
    """Normaliza ``component.config.relation`` sem conhecer Django/ORM."""
    if not isinstance(raw, dict):
        raise AdvancedPageContractError(
            "invalid_relation_config",
            "Binding relacional exige config.relation válido.",
            page_id=page_id,
            component_id=component_id,
        )

    source = str(raw.get("source") or RELATION_SOURCE_PAGE_CONTEXT).strip()
    target_field = str(raw.get("target_field") or "").strip()
    source_field = str(raw.get("source_field") or "pk").strip()

    if source != RELATION_SOURCE_PAGE_CONTEXT:
        raise AdvancedPageContractError(
            "unsupported_relation_source",
            "Fonte relacional não suportada. Use o contexto atual da página.",
            page_id=page_id,
            component_id=component_id,
        )
    if not target_field or "__" in target_field or "." in target_field or "/" in target_field:
        raise AdvancedPageContractError(
            "invalid_relation_target_field",
            "Campo relacional de destino inválido.",
            page_id=page_id,
            component_id=component_id,
        )
    if source_field not in RELATION_SOURCE_FIELDS:
        raise AdvancedPageContractError(
            "unsupported_relation_source_field",
            "Nesta fase, a relação deve usar a chave primária do registro atual.",
            page_id=page_id,
            component_id=component_id,
        )

    return {
        "source": RELATION_SOURCE_PAGE_CONTEXT,
        "source_field": source_field,
        "target_field": target_field,
    }


def normalize_component_relation(component, page, entities):
    """Valida e normaliza a relação de um componente contra o domínio conhecido."""
    config = component.get("config") if isinstance(component.get("config"), dict) else {}
    raw_relation = config.get("relation")
    if raw_relation is None:
        return component

    page_id = page["id"]
    component_id = component["id"]
    context = page.get("context") or {}
    binding = component.get("binding") or {}

    if context.get("kind") != "record" or not context.get("entity"):
        raise AdvancedPageContractError(
            "relation_requires_record_context",
            "Binding relacional exige página com contexto de um registro.",
            page_id=page_id,
            component_id=component_id,
        )
    if binding.get("kind") != "entity" or not binding.get("ref"):
        raise AdvancedPageContractError(
            "relation_requires_entity_binding",
            "Binding relacional exige binding de entidade como destino.",
            page_id=page_id,
            component_id=component_id,
        )

    relation = normalize_relation_config(raw_relation, page_id=page_id, component_id=component_id)
    target_entity_name = binding["ref"]
    target_entity = entities.get(target_entity_name)
    if target_entity is None:
        raise AdvancedPageContractError(
            "unknown_relation_target_entity",
            "Relação referencia entidade de destino inexistente.",
            page_id=page_id,
            component_id=component_id,
        )

    fields = target_entity.get("fields_meta") or {}
    target_field = fields.get(relation["target_field"])
    if target_field is None:
        raise AdvancedPageContractError(
            "unknown_relation_target_field",
            "Relação referencia campo inexistente na entidade de destino.",
            page_id=page_id,
            component_id=component_id,
        )

    field_type = str(target_field.get("type") or target_field.get("tipo") or "").strip()
    if field_type not in RELATIONAL_FIELD_TYPES:
        raise AdvancedPageContractError(
            "relation_target_not_relational",
            "Campo de destino deve ser relacional.",
            page_id=page_id,
            component_id=component_id,
        )

    related_entity = str(
        target_field.get("related_entity")
        or target_field.get("entidade_relacionada")
        or target_field.get("related_entity_name")
        or ""
    ).strip()
    if related_entity != context["entity"]:
        raise AdvancedPageContractError(
            "relation_context_entity_mismatch",
            "Campo relacional de destino não aponta para a entidade do contexto atual.",
            page_id=page_id,
            component_id=component_id,
        )

    normalized = deepcopy(component)
    normalized_config = deepcopy(config)
    normalized_config["relation"] = relation
    normalized["config"] = normalized_config
    return normalized
