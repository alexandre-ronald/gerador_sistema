from django import template

register = template.Library()

CRUD_EVENTS = {"created", "updated", "deleted"}
WORKFLOW_EVENT = "workflow_transition"
EVENTS = CRUD_EVENTS | {WORKFLOW_EVENT}
AUDIENCES = {"users_with_view_permission", "actor", "role"}


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


def _entity_rules(entities, entity_name):
    structure = _stored_structure(_system_from_entities(entities))
    notifications = structure.get("notifications")
    if not isinstance(notifications, dict):
        return []
    raw_rules = notifications.get(entity_name)
    if not isinstance(raw_rules, list):
        return []

    result = []
    for raw in raw_rules:
        if not isinstance(raw, dict) or raw.get("enabled", True) is not True:
            continue
        event = str(raw.get("event") or "").strip()
        audience = str(raw.get("audience") or "").strip()
        rule_id = str(raw.get("id") or "").strip()
        title = str(raw.get("title") or "").strip()
        message = str(raw.get("message") or "").strip()
        transition = str(raw.get("transition") or "").strip()
        role = str(raw.get("role") or "").strip()
        if not rule_id or event not in EVENTS or audience not in AUDIENCES or not title or not message:
            continue
        if event == WORKFLOW_EVENT and not transition:
            continue
        if event != WORKFLOW_EVENT and transition:
            continue
        if audience == "role" and not role:
            continue
        if audience != "role" and role:
            continue
        result.append({
            "id": rule_id,
            "event": event,
            "transition": transition,
            "title": title,
            "message": message,
            "audience": audience,
            "role": role,
        })
    return result


@register.simple_tag
def notification_entity_rules(entities, entity_name):
    return _entity_rules(entities, entity_name)


@register.simple_tag
def module_has_notifications(entities):
    return any(_entity_rules(entities, getattr(entity, "nome", "")) for entity in (entities or []))
