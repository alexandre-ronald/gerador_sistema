"""GEN-071.3 — métricas seguras derivadas de coleções relacionadas."""
from copy import deepcopy

from .advanced_pages import AdvancedPageContractError


AGGREGATE_OPERATIONS = ("count", "sum", "avg", "min", "max")
NUMERIC_FIELD_TYPES = ("IntegerField", "FloatField", "DecimalField")
ORDERABLE_FIELD_TYPES = NUMERIC_FIELD_TYPES + ("DateField", "DateTimeField", "TimeField")


def normalize_related_metric(component, entities, *, page_id):
    """Normaliza ``component.config.aggregate`` para métricas relacionais.

    A métrica só é considerada relacional quando o componente ``metric`` possui
    também ``config.relation``. O contrato não aceita expressões, funções ou
    lookups livres; apenas operações conhecidas sobre um campo direto da entidade.
    """
    config = component.get("config") if isinstance(component.get("config"), dict) else {}
    relation = config.get("relation")
    aggregate = config.get("aggregate")
    if relation is None and aggregate is None:
        return component

    component_id = component.get("id")
    if component.get("type") != "metric" or relation is None:
        if aggregate is not None:
            raise AdvancedPageContractError(
                "aggregate_requires_related_metric",
                "Agregação relacional exige componente de métrica com relação configurada.",
                page_id=page_id,
                component_id=component_id,
            )
        return component

    raw = aggregate if isinstance(aggregate, dict) else {}
    operation = str(raw.get("operation") or "count").strip().lower()
    field_name = str(raw.get("field") or "").strip()
    if operation not in AGGREGATE_OPERATIONS:
        raise AdvancedPageContractError(
            "unknown_aggregate_operation",
            "Operação de métrica relacional desconhecida.",
            page_id=page_id,
            component_id=component_id,
        )

    entity_name = str((component.get("binding") or {}).get("ref") or "").strip()
    entity = entities.get(entity_name) or {}
    fields = entity.get("fields_meta") or {}

    if operation == "count":
        field_name = ""
    else:
        if not field_name or "__" in field_name or "." in field_name or "/" in field_name:
            raise AdvancedPageContractError(
                "aggregate_field_required",
                "A operação selecionada exige um campo direto da entidade relacionada.",
                page_id=page_id,
                component_id=component_id,
            )
        field = fields.get(field_name)
        if field is None:
            raise AdvancedPageContractError(
                "unknown_aggregate_field",
                "Métrica relacional referencia campo inexistente.",
                page_id=page_id,
                component_id=component_id,
            )
        field_type = str(field.get("type") or field.get("tipo") or "").strip()
        allowed_types = NUMERIC_FIELD_TYPES if operation in {"sum", "avg"} else ORDERABLE_FIELD_TYPES
        if field_type not in allowed_types:
            raise AdvancedPageContractError(
                "incompatible_aggregate_field",
                "O tipo do campo não é compatível com a operação selecionada.",
                page_id=page_id,
                component_id=component_id,
            )

    normalized = deepcopy(component)
    normalized_config = deepcopy(config)
    normalized_config["aggregate"] = {"operation": operation, "field": field_name}
    normalized["config"] = normalized_config
    return normalized
