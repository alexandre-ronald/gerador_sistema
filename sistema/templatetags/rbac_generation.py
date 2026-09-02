from copy import deepcopy

from django import template

from sistema.rbac import CRUD_ACTIONS, normalize_rbac_config

register = template.Library()


def _empty_config():
    return {"enabled": False, "roles": [], "entities": {}}


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
