"""Contratos canônicos dos recursos configuráveis do System Builder."""
import hashlib
import json

CRUD_ACTIONS = ("list", "detail", "create", "update", "delete")
MENU_STYLES = ("lateral", "superior")
DENSITIES = ("compact", "comfortable", "spacious")


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
    """Return a deterministic JSON-safe snapshot used to decide what changed."""
    if not isinstance(spec, dict): return {}
    return json.loads(json.dumps(spec, ensure_ascii=False, sort_keys=True, default=str))


def spec_fingerprint(spec):
    canonical = canonicalize_spec(spec)
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def diff_top_level(previous, current):
    """Small deterministic diff; deeper generators can consume the changed sections."""
    before, after = canonicalize_spec(previous), canonicalize_spec(current)
    keys = sorted(set(before) | set(after))
    return [key for key in keys if before.get(key) != after.get(key)]
