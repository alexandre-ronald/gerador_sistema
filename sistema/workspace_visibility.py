"""GEN-072.4 — visibilidade de Workspace derivada do RBAC existente.

Workspace não concede permissões. Esta camada apenas projeta o contrato de navegação
para um conjunto de papéis já resolvido pelo runtime/preview.
"""
from copy import deepcopy

from .workspace_contract import normalize_workspace_config


def _role_ids(value):
    return {str(item).strip() for item in (value or []) if str(item).strip()}


def _crud_allowed(rbac, entity_name, operation, roles):
    policy = ((rbac.get("entities") or {}).get(entity_name) or {}).get("roles") or {}
    return any(operation in (policy.get(role_id) or []) for role_id in roles)


def _report_allowed(rbac, ref, roles):
    if ":" not in ref:
        return False
    entity_name, report_id = ref.split(":", 1)
    allowed = (((rbac.get("reports") or {}).get(entity_name) or {}).get(report_id))
    return isinstance(allowed, list) and bool(_role_ids(allowed).intersection(roles))


def _advanced_page_allowed(structure, ref, rbac, roles):
    pages = ((structure.get("advanced_pages") or {}).get("pages") or [])
    page = next((item for item in pages if isinstance(item, dict) and item.get("id") == ref and item.get("enabled") is True), None)
    if not page:
        return False
    context = page.get("context") if isinstance(page.get("context"), dict) else {}
    entity_name = str(context.get("entity") or "").strip()
    if not entity_name:
        return True
    return _crud_allowed(rbac, entity_name, "view" if context.get("kind") == "record" else "list", roles)


def workspace_destination_visible(destination, *, structure, rbac, role_ids):
    """Retorna somente visibilidade; nunca altera ou amplia o contrato RBAC."""
    rbac = rbac if isinstance(rbac, dict) else {}
    if not rbac.get("enabled"):
        return True
    roles = _role_ids(role_ids)
    if not roles:
        return False
    kind = destination.get("kind")
    ref = str(destination.get("ref") or "")
    if kind == "crud":
        return _crud_allowed(rbac, ref, destination.get("operation") or "list", roles)
    if kind == "report":
        return _report_allowed(rbac, ref, roles)
    if kind == "advanced_page":
        return _advanced_page_allowed(structure if isinstance(structure, dict) else {}, ref, rbac, roles)
    if kind == "dashboard":
        # Dashboard ainda não possui política própria no contrato RBAC. Quando RBAC está
        # ativo, ele só é visível a quem possui ao menos uma capacidade de consulta.
        return any(_crud_allowed(rbac, entity, "list", roles) for entity in (rbac.get("entities") or {}))
    return False


def visible_workspace_config(raw_config, *, structure, rbac, role_ids):
    """Projeta apenas workspaces/seções/itens autorizados e resolve home com fallback seguro."""
    config = normalize_workspace_config(raw_config, strict=True)
    projected = []
    for workspace in config["workspaces"]:
        sections = []
        visible_item_ids = []
        for section in workspace["sections"]:
            items = [
                deepcopy(item)
                for item in section["items"]
                if workspace_destination_visible(item["destination"], structure=structure, rbac=rbac, role_ids=role_ids)
            ]
            if items:
                visible_item_ids.extend(item["id"] for item in items)
                section_copy = deepcopy(section)
                section_copy["items"] = items
                sections.append(section_copy)
        if not sections:
            continue
        workspace_copy = deepcopy(workspace)
        workspace_copy["sections"] = sections
        if workspace_copy.get("home") not in visible_item_ids:
            workspace_copy["home"] = visible_item_ids[0] if visible_item_ids else ""
        projected.append(workspace_copy)

    visible_ids = {workspace["id"] for workspace in projected}
    default_workspace = config.get("default_workspace")
    if default_workspace not in visible_ids:
        default_workspace = projected[0]["id"] if projected else ""
    return {"version": config["version"], "default_workspace": default_workspace, "workspaces": projected}
