"""GEN-072.5/072.7/072.8 — projeção de Workspace para o Application Preview Studio."""
from copy import deepcopy
from urllib.parse import urlencode

from .workspace_contract import normalize_workspace_config
from .workspace_navigation_context import resolve_active_workspace
from .workspace_visibility import visible_workspace_config


def _role_ids(role_simulation):
    if role_simulation.get("invalid_role"):
        return []
    if role_simulation.get("active") and role_simulation.get("selected_role_id"):
        return [role_simulation["selected_role_id"]]
    return []


def _item_url(item, entity_ids, *, workspace_id=""):
    destination = item["destination"]
    kind = destination["kind"]
    ref = destination["ref"]
    params = {}
    if kind == "crud":
        entity_id = entity_ids.get(ref)
        if entity_id:
            params = {"entidade": entity_id, "pagina": "list"}
    elif kind == "dashboard":
        params = {"pagina": "dashboard"}
    elif kind == "report":
        if ":" in ref:
            entity_name, report_id = ref.split(":", 1)
            entity_id = entity_ids.get(entity_name)
            if entity_id:
                params = {"entidade": entity_id, "pagina": "report", "relatorio": report_id}
    elif kind == "workflow":
        entity_id = entity_ids.get(ref)
        if entity_id:
            params = {"entidade": entity_id, "pagina": "workflow"}
    elif kind == "advanced_page":
        params = {"pagina": "advanced", "pagina_avancada": ref}
    if not params:
        return ""
    if workspace_id:
        params["workspace"] = workspace_id
        params["workspace_item"] = item.get("id") or ""
    return f"?{urlencode(params)}"


def _project_workspace(workspace, entity_ids):
    projected_workspace = deepcopy(workspace)
    sections = []
    home_url = ""
    for section in workspace.get("sections") or []:
        if not section.get("enabled"):
            continue
        items = []
        for item in section.get("items") or []:
            if not item.get("enabled"):
                continue
            projected = deepcopy(item)
            projected["url"] = _item_url(item, entity_ids, workspace_id=workspace.get("id") or "")
            projected["active"] = False
            items.append(projected)
            if item.get("id") == workspace.get("home"):
                home_url = projected["url"]
        if items:
            section_copy = deepcopy(section)
            section_copy["items"] = items
            sections.append(section_copy)
    projected_workspace["sections"] = sections
    if not home_url and sections and sections[0].get("items"):
        home_url = sections[0]["items"][0].get("url") or ""
    projected_workspace["home_url"] = home_url
    return projected_workspace


def project_workspace_preview(structure, *, role_simulation, entities, selected_workspace_id=""):
    """Projeta o contrato persistido sem criar estado próprio no Preview."""
    structure = structure if isinstance(structure, dict) else {}
    raw = structure.get("workspaces") if isinstance(structure.get("workspaces"), dict) else None
    config = normalize_workspace_config(raw, strict=False)
    rbac = structure.get("rbac") if isinstance(structure.get("rbac"), dict) else {}

    if rbac.get("enabled") and (role_simulation.get("active") or role_simulation.get("invalid_role")):
        config = visible_workspace_config(
            config,
            structure=structure,
            rbac=rbac,
            role_ids=_role_ids(role_simulation),
        )

    enabled = [deepcopy(workspace) for workspace in config["workspaces"] if workspace.get("enabled")]
    visible_ids = {workspace["id"] for workspace in enabled}
    requested = str(selected_workspace_id or "").strip()
    active_workspace = resolve_active_workspace(
        {
            "workspaces": enabled,
            "default_workspace": config.get("default_workspace"),
        },
        workspace_id=requested,
    )
    selected_id = active_workspace.get("id") if active_workspace else ""

    entity_ids = {entity.nome: entity.pk for entity in entities or []}
    projected_workspaces = [_project_workspace(workspace, entity_ids) for workspace in enabled]
    selected = next((workspace for workspace in projected_workspaces if workspace.get("id") == selected_id), None)

    return {
        "configured": bool(config["workspaces"]),
        "workspaces": projected_workspaces,
        "selected": selected,
        "selected_id": selected_id,
        "requested_id": requested,
        "invalid_selection": bool(requested and requested not in visible_ids),
        "empty_for_role": bool(config.get("workspaces") == [] and raw),
    }
