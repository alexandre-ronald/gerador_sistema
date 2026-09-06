"""GEN-071.3 — projeção demonstrativa de métricas relacionais no Preview."""


def enrich_related_metrics_preview(preview):
    page = preview.get("advanced_page") if isinstance(preview, dict) else None
    if not isinstance(page, dict):
        return preview

    operation_labels = {
        "count": "Contagem",
        "sum": "Soma",
        "avg": "Média",
        "min": "Mínimo",
        "max": "Máximo",
    }
    demo_values = {
        "count": "7",
        "sum": "2.840.000",
        "avg": "405.714",
        "min": "120.000",
        "max": "860.000",
    }

    for component in page.get("components_projection") or []:
        if not isinstance(component, dict) or component.get("type") != "metric":
            continue
        config = component.get("config") if isinstance(component.get("config"), dict) else {}
        relation = config.get("relation") if isinstance(config.get("relation"), dict) else None
        aggregate = config.get("aggregate") if isinstance(config.get("aggregate"), dict) else None
        if not relation or not aggregate:
            continue
        operation = str(aggregate.get("operation") or "count").strip().lower()
        field = str(aggregate.get("field") or "").strip()
        entity = str((component.get("binding") or {}).get("ref") or "").strip()
        component["demo_value"] = demo_values.get(operation, "—")
        component["special"] = {
            **(component.get("special") or {}),
            "related_metric": True,
            "aggregate_operation": operation,
            "aggregate_label": operation_labels.get(operation, operation),
            "aggregate_field": field,
            "relation_summary": f"{entity}.{relation.get('target_field')} = contexto.pk",
        }
    return preview
