"""GEN-072.5/072.7 — projeção de Workspace para o Application Preview Studio."""
from copy import deepcopy
from urllib.parse import urlencode

from .workspace_contract import normalize_workspace_config
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
    selected_id = requested if requested in visible_ids else config.get("default_workspace")
    if selected_id not in visible_ids:
        selected_id = enabled[0]["id"] if enabled else ""
    selected = next((workspace for workspace in enabled if workspace["id"] == selected_id), None)

    entity_ids = {entity.nome: entity.pk for entity in entities or []}
    if selected:
        sections = []
        for section in selected["sections"]:
            if not section.get("enabled"):
                continue
            items = []
            for item in section["items"]:
                if not item.get("enabled"):
                    continue
                projected = deepcopy(item)
                projected["url"] = _item_url(item, entity_ids, workspace_id=selected_id)
                projected["active"] = False
                items.append(projected)
            if items:
                section_copy = deepcopy(section)
                section_copy["items"] = items
                sections.append(section_copy)
        selected["sections"] = sections

    return {
        "configured": bool(config["workspaces"]),
        "workspaces": enabled,
        "selected": selected,
        "selected_id": selected_id,
        "requested_id": requested,
        "invalid_selection": bool(requested and requested not in visible_ids),
        "empty_for_role": bool(config.get("workspaces") == [] and raw),
    }
