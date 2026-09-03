from copy import deepcopy
import keyword
import re

from django import template
from django.utils.text import slugify

from sistema.rbac import CRUD_ACTIONS, normalize_rbac_config

register = template.Library()


def _empty_config():
    return {"enabled": False, "roles": [], "entities": {}}


def _python_identifier(value, fallback="item"):
    value = slugify(str(value or ""), allow_unicode=False).replace("-", "_")
    value = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_") or fallback
    if value[0].isdigit():
        value = f"_{value}"
    if keyword.iskeyword(value):
        value = f"{value}_"
    return value


def _system_from_entities(entities):
    for entidade in entities or []:
        modulo = getattr(entidade, "modulo", None)
        sistema = getattr(modulo, "sistema", None) if modulo is not None else None
        if sistema is not None:
            return sistema
    return None


def _stored_structure(sistema):
    if sistema is None:
        return {}
    versao = sistema.versoes.filter(numero=0).first()
    return versao.estrutura_json if versao and isinstance(versao.estrutura_json, dict) else {}


def _metadata(entities):
    return [
        {"name": getattr(entidade, "nome", ""), "label": getattr(entidade, "nome", "")}
        for entidade in (entities or [])
        if getattr(entidade, "nome", "")
    ]


def _system_entities(sistema):
    if sistema is None:
        return []
    result = []
    for modulo in sistema.modulos.prefetch_related("entidades").all():
        result.extend(list(modulo.entidades.all()))
    return result


def _system_config(sistema):
    structure = _stored_structure(sistema)
    raw = structure.get("rbac")
    if not isinstance(raw, dict):
        return _empty_config()
    workflows = structure.get("workflows") if isinstance(structure.get("workflows"), dict) else {}
    return normalize_rbac_config(_metadata(_system_entities(sistema)), workflows, raw, strict=True)


def _runtime_system_config(sistema):
    config = _system_config(sistema)
    if not config.get("enabled"):
        return {"enabled": False, "roles": []}

    entities = {getattr(entity, "nome", ""): entity for entity in _system_entities(sistema)}
    roles = {role["id"]: {**role, "permissions": []} for role in config.get("roles", [])}
    action_map = {"list": "view", "view": "view", "create": "add", "update": "change", "delete": "delete"}

    for entity_name, policy in (config.get("entities") or {}).items():
        entity = entities.get(entity_name)
        if entity is None:
            continue
        app_label = _python_identifier(entity.modulo.nome, "app")
        model_name = _python_identifier(entity.nome, "entidade")
        for role_id, actions in (policy.get("roles") or {}).items():
            role = roles.get(role_id)
            if role is None:
                continue
            seen = {(item["app_label"], item["codename"]) for item in role["permissions"]}
            for action in actions:
                django_action = action_map.get(action)
                if not django_action:
                    continue
                permission = {"app_label": app_label, "codename": f"{django_action}_{model_name}"}
                key = (permission["app_label"], permission["codename"])
                if key not in seen:
                    role["permissions"].append(permission)
                    seen.add(key)

    return {"enabled": True, "roles": sorted(roles.values(), key=lambda item: (item.get("order", 0), item["label"].casefold()))}


def _config(entities):
    entities = list(entities or [])
    sistema = _system_from_entities(entities)
    structure = _stored_structure(sistema)
    raw = structure.get("rbac")
    if not isinstance(raw, dict):
        return _empty_config()
    workflows = structure.get("workflows") if isinstance(structure.get("workflows"), dict) else {}
    return normalize_rbac_config(_metadata(entities), workflows, raw, strict=True)


def _entity_policy(entities, entity_name):
    config = _config(entities)
    policy = (config.get("entities") or {}).get(entity_name) or {"roles": {}, "transitions": {}}
    return {"enabled": bool(config.get("enabled")), **deepcopy(policy)}


@register.simple_tag
def rbac_generation_config(entities):
    return _config(entities)


@register.simple_tag
def rbac_system_config(sistema):
    return _system_config(sistema)


@register.simple_tag
def rbac_system_runtime_config(sistema):
    return _runtime_system_config(sistema)


@register.simple_tag
def rbac_entity_policy(entities, entity_name):
    return _entity_policy(entities, entity_name)


@register.simple_tag
def rbac_action_groups(entities, entity_name, action):
    if action not in CRUD_ACTIONS:
        return []
    config = _config(entities)
    if not config.get("enabled"):
        return []
    roles = {item["id"]: item for item in config.get("roles", [])}
    policy = (config.get("entities") or {}).get(entity_name) or {}
    result = []
    for role_id, actions in (policy.get("roles") or {}).items():
        if action in actions and role_id in roles:
            result.append(roles[role_id]["group"])
    return result


@register.simple_tag
def rbac_transition_groups(entities, entity_name, transition_id):
    config = _config(entities)
    if not config.get("enabled"):
        return []
    roles = {item["id"]: item for item in config.get("roles", [])}
    policy = (config.get("entities") or {}).get(entity_name) or {}
    role_ids = (policy.get("transitions") or {}).get(transition_id, [])
    return [roles[role_id]["group"] for role_id in role_ids if role_id in roles]


@register.simple_tag
def module_has_rbac(entities):
    return bool(_config(entities).get("enabled"))
