from copy import deepcopy

OPERATIONS = {"count", "sum", "avg", "min", "max"}


def normalize_query(config=None):
    config = deepcopy(config or {})
    operation = str(config.get("operation") or "count").lower()
    if operation not in OPERATIONS:
        operation = "count"
    try:
        limit = int(config.get("limit") or 20)
    except (TypeError, ValueError):
        limit = 20
    return {
        "operation": operation,
        "field": config.get("field") or "id",
        "group_by": config.get("group_by") or None,
        "fields": list(config.get("fields") or []),
        "limit": max(1, min(limit, 100)),
        "order": config.get("order") or "-total",
    }
