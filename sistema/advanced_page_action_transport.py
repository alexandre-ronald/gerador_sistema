"""GEN-071.4 — transporte declarativo do contexto atual para ações.

Primeira fatia funcional: uma ação CRUD ``create`` pode transportar a chave
primária do registro atual para um campo relacional da entidade criada.

Exemplo:
    Central do Fornecedor -> Novo Contrato
    Contrato.fornecedor <- page_context.pk
"""
from copy import deepcopy

from .advanced_pages import AdvancedPageContractError
from .advanced_page_relations import RELATIONAL_FIELD_TYPES


TRANSPORT_SOURCE_PAGE_CONTEXT = "page_context"
TRANSPORT_SOURCE_FIELDS = ("pk",)


def normalize_action_transport(action, page, entities):
    raw = action.get("transport")
    if raw is None:
        return action
    if not isinstance(raw, dict):
        raise AdvancedPageContractError(
            "invalid_action_transport",
            "Transporte de contexto da ação é inválido.",
            page_id=page["id"],
            action_id=action["id"],
        )

    if action.get("kind") != "crud" or (action.get("target") or {}).get("operation") != "create":
        raise AdvancedPageContractError(
            "transport_requires_crud_create",
            "Nesta fase, transporte de contexto exige ação CRUD de criação.",
            page_id=page["id"],
            action_id=action["id"],
        )

    context = page.get("context") or {}
    if context.get("kind") != "record" or not context.get("entity"):
        raise AdvancedPageContractError(
            "transport_requires_record_context",
            "Transporte de contexto exige página com contexto de um registro.",
            page_id=page["id"],
            action_id=action["id"],
        )

    source = str(raw.get("source") or TRANSPORT_SOURCE_PAGE_CONTEXT).strip()
    source_field = str(raw.get("source_field") or "pk").strip()
    target_field = str(raw.get("target_field") or "").strip()

    if source != TRANSPORT_SOURCE_PAGE_CONTEXT:
        raise AdvancedPageContractError(
            "unsupported_transport_source",
            "Fonte de transporte não suportada.",
            page_id=page["id"],
            action_id=action["id"],
        )
    if source_field not in TRANSPORT_SOURCE_FIELDS:
        raise AdvancedPageContractError(
            "unsupported_transport_source_field",
            "Nesta fase, o transporte deve usar a chave primária do registro atual.",
            page_id=page["id"],
            action_id=action["id"],
        )
    if not target_field or "__" in target_field or "." in target_field or "/" in target_field:
        raise AdvancedPageContractError(
            "invalid_transport_target_field",
            "Campo de destino do transporte é inválido.",
            page_id=page["id"],
            action_id=action["id"],
        )

    target_entity_name = str((action.get("target") or {}).get("entity") or "").strip()
    target_entity = entities.get(target_entity_name)
    if target_entity is None:
        raise AdvancedPageContractError(
            "unknown_transport_target_entity",
            "Transporte referencia entidade de destino inexistente.",
            page_id=page["id"],
            action_id=action["id"],
        )

    target_field_meta = (target_entity.get("fields_meta") or {}).get(target_field)
    if target_field_meta is None:
        raise AdvancedPageContractError(
            "unknown_transport_target_field",
            "Transporte referencia campo inexistente na entidade de destino.",
            page_id=page["id"],
            action_id=action["id"],
        )

    field_type = str(target_field_meta.get("type") or target_field_meta.get("tipo") or "").strip()
    if field_type not in RELATIONAL_FIELD_TYPES:
        raise AdvancedPageContractError(
            "transport_target_not_relational",
            "Campo de destino do transporte deve ser relacional.",
            page_id=page["id"],
            action_id=action["id"],
        )

    related_entity = str(
        target_field_meta.get("related_entity")
        or target_field_meta.get("entidade_relacionada")
        or target_field_meta.get("related_entity_name")
        or ""
    ).strip()
    if related_entity != context.get("entity"):
        raise AdvancedPageContractError(
            "transport_context_entity_mismatch",
            "Campo de destino não aponta para a entidade do contexto atual.",
            page_id=page["id"],
            action_id=action["id"],
        )

    normalized = deepcopy(action)
    normalized["transport"] = {
        "source": TRANSPORT_SOURCE_PAGE_CONTEXT,
        "source_field": "pk",
        "target_field": target_field,
    }
    return normalized
