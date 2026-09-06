"""GEN-070.6 — decisões de autorização compartilháveis pelo runtime gerado.

Este módulo não renderiza UI e não depende de request. Ele recebe contratos já
persistidos e responde somente decisões explícitas, mantendo política ativa em
modo fail-closed.
"""
from dataclasses import dataclass

from .rbac import CRUD_ACTION_SET, entity_policy, report_roles, role_map


@dataclass(frozen=True)
class RuntimeDecision:
    allowed: bool
    code: str


def _enabled(rbac):
    return isinstance(rbac, dict) and rbac.get("enabled") is True


def _known_role(rbac, role_id):
    return bool(role_id) and role_id in role_map(rbac)


def _inactive_or_role(rbac, role_id):
    if not _enabled(rbac):
        return RuntimeDecision(True, "rbac_inactive")
    if not _known_role(rbac, role_id):
        return RuntimeDecision(False, "unknown_or_missing_role")
    return None


def can_crud(rbac, role_id, entity_name, action):
    gate = _inactive_or_role(rbac, role_id)
    if gate:
        return gate
    if action not in CRUD_ACTION_SET:
        return RuntimeDecision(False, "unknown_crud_action")
    policy = entity_policy(rbac, entity_name)
    if not policy:
        return RuntimeDecision(False, "missing_entity_policy")
    actions = (policy.get("roles") or {}).get(role_id)
    if not isinstance(actions, list):
        return RuntimeDecision(False, "missing_role_grant")
    return RuntimeDecision(action in actions, "granted" if action in actions else "crud_denied")


def can_workflow_transition(rbac, role_id, entity_name, transition_id):
    gate = _inactive_or_role(rbac, role_id)
    if gate:
        return gate
    policy = entity_policy(rbac, entity_name)
    if not policy:
        return RuntimeDecision(False, "missing_entity_policy")
    roles = (policy.get("transitions") or {}).get(transition_id)
    if not isinstance(roles, list):
        return RuntimeDecision(False, "missing_transition_policy")
    return RuntimeDecision(role_id in roles, "granted" if role_id in roles else "workflow_denied")


def can_report(rbac, role_id, entity_name, report_id):
    gate = _inactive_or_role(rbac, role_id)
    if gate:
        return gate
    roles = report_roles(rbac, entity_name, report_id)
    if not isinstance(roles, list):
        return RuntimeDecision(False, "missing_report_policy")
    return RuntimeDecision(role_id in roles, "granted" if role_id in roles else "report_denied")


def can_action(rbac, role_id, action):
    """Autoriza uma ação normalizada do Advanced Page Designer.

    Navegação entre páginas não cria uma permissão paralela. As demais ações
    delegam para a capacidade original (CRUD/workflow/report).
    """
    gate = _inactive_or_role(rbac, role_id)
    if gate:
        return gate
    if not isinstance(action, dict):
        return RuntimeDecision(False, "invalid_action")
    kind = action.get("kind")
    target = action.get("target") if isinstance(action.get("target"), dict) else {}
    if kind == "navigate":
        return RuntimeDecision(bool(target.get("page")), "granted" if target.get("page") else "invalid_navigation_target")
    if kind == "crud":
        return can_crud(rbac, role_id, target.get("entity"), target.get("operation"))
    if kind == "workflow":
        return can_workflow_transition(rbac, role_id, target.get("entity"), target.get("transition"))
    if kind == "report":
        return can_report(rbac, role_id, target.get("entity"), target.get("report"))
    return RuntimeDecision(False, "unknown_action_kind")


def visible_actions(rbac, role_id, actions):
    return [action for action in (actions or []) if can_action(rbac, role_id, action).allowed]
