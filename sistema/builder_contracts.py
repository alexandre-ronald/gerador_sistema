"""Contratos canônicos dos recursos configuráveis do System Builder."""
import hashlib
import json

CRUD_ACTIONS = ("list", "detail", "create", "update", "delete")
MENU_STYLES = ("lateral", "superior")
DENSITIES = ("compact", "comfortable", "spacious")
WIDGET_TYPES = ("metric", "table", "bar", "line", "area", "pie", "donut")


def default_crud_config():
    return {"enabled": True, "actions": list(CRUD_ACTIONS), "search_fields": [], "filter_fields": [], "ordering": [], "page_size": 25, "confirm_delete": True, "bulk_actions": []}


def normalize_crud_config(value=None):
    config = default_crud_config()
    if isinstance(value, dict): config.update({k: v for k, v in value.items() if k in config})
    config["enabled"] = bool(config["enabled"])
    config["actions"] = [x for x in config["actions"] if x in CRUD_ACTIONS]
    for key in ("search_fields", "filter_fields", "ordering", "bulk_actions"): config[key] = list(dict.fromkeys(config[key] or []))
    try: config["page_size"] = max(1, min(200, int(config["page_size"])))
    except (TypeError, ValueError): config["page_size"] = 25
    return config


def crud_capabilities(config):
    normalized = normalize_crud_config(config)
    return {action: action in normalized["actions"] for action in CRUD_ACTIONS}


def default_theme_config():
    return {"menu": "lateral", "density": "comfortable", "dark_mode": "system", "brand_name": "", "primary_color": "", "accent_color": "", "show_breadcrumbs": True, "show_search": True, "show_user_menu": True}


def normalize_theme_config(value=None):
    config = default_theme_config()
    if isinstance(value, dict): config.update({k: v for k, v in value.items() if k in config})
    if config["menu"] not in MENU_STYLES: config["menu"] = "lateral"
    if config["density"] not in DENSITIES: config["density"] = "comfortable"
    if config["dark_mode"] not in ("system", "light", "dark"): config["dark_mode"] = "system"
    for key in ("show_breadcrumbs", "show_search", "show_user_menu"): config[key] = bool(config[key])
    return config


def canonicalize_spec(spec):
    if not isinstance(spec, dict): return {}
    return json.loads(json.dumps(spec, ensure_ascii=False, sort_keys=True, default=str))


def spec_fingerprint(spec):
    raw = json.dumps(canonicalize_spec(spec), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def diff_top_level(previous, current):
    before, after = canonicalize_spec(previous), canonicalize_spec(current)
    return [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]


def default_dashboard_config():
    return {
        "enabled": True,
        "title": "Dashboard",
        "layout": "12-column",
        "refresh_seconds": 0,
        "widgets": [],
    }


def normalize_widget(widget):
    widget = widget if isinstance(widget, dict) else {}
    kind = widget.get("type", "metric")
    if kind not in WIDGET_TYPES: kind = "metric"
    return {
        "id": str(widget.get("id") or "widget"),
        "type": kind,
        "title": str(widget.get("title") or "Sem título"),
        "entity": str(widget.get("entity") or ""),
        "x": max(0, min(11, int(widget.get("x", 0)))),
        "y": max(0, int(widget.get("y", 0))),
        "w": max(1, min(12, int(widget.get("w", 4)))),
        "h": max(1, min(12, int(widget.get("h", 3)))),
        "config": widget.get("config") if isinstance(widget.get("config"), dict) else {},
    }


def normalize_dashboard_config(value=None):
    config = default_dashboard_config()
    if isinstance(value, dict): config.update({k: v for k, v in value.items() if k in config})
    try: config["refresh_seconds"] = max(0, int(config["refresh_seconds"]))
    except (TypeError, ValueError): config["refresh_seconds"] = 0
    config["widgets"] = [normalize_widget(w) for w in (config["widgets"] or [])]
    return config
