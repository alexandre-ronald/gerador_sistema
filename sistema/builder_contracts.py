"""Contratos canônicos dos recursos configuráveis do System Builder.

Este módulo não renderiza HTML nem gera código. Ele normaliza a especificação
antes da geração para evitar que regras de UI sejam duplicadas no pipeline.
"""

CRUD_ACTIONS = ("list", "detail", "create", "update", "delete")


def default_crud_config():
    return {
        "enabled": True,
        "actions": list(CRUD_ACTIONS),
        "search_fields": [],
        "filter_fields": [],
        "ordering": [],
        "page_size": 25,
        "confirm_delete": True,
        "bulk_actions": [],
    }


def normalize_crud_config(value=None):
    config = default_crud_config()
    if isinstance(value, dict):
        config.update({k: v for k, v in value.items() if k in config})
    config["enabled"] = bool(config["enabled"])
    config["actions"] = [x for x in config["actions"] if x in CRUD_ACTIONS]
    config["search_fields"] = list(dict.fromkeys(config["search_fields"] or []))
    config["filter_fields"] = list(dict.fromkeys(config["filter_fields"] or []))
    config["ordering"] = list(dict.fromkeys(config["ordering"] or []))
    config["bulk_actions"] = list(dict.fromkeys(config["bulk_actions"] or []))
    try:
        config["page_size"] = max(1, min(200, int(config["page_size"])))
    except (TypeError, ValueError):
        config["page_size"] = 25
    return config


def crud_capabilities(config):
    normalized = normalize_crud_config(config)
    return {action: action in normalized["actions"] for action in CRUD_ACTIONS}
