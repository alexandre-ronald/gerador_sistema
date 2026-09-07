"""GEN-072.2 — resolução semântica dos destinos de Workspace.

Esta camada valida existência e navegabilidade. Autorização por papel pertence à GEN-072.4.
"""
from copy import deepcopy

from .advanced_pages import normalize_advanced_pages_config
from .builder_contracts import normalize_dashboard_config
from .workspace_contract import WorkspaceContractError, normalize_workspace_config


class WorkspaceSemanticError(WorkspaceContractError):
    pass


def _fail(code, message, *, workspace_id, section_id, item_id):
    raise WorkspaceSemanticError(code, message, workspace_id=workspace_id, section_id=section_id, item_id=item_id)


def _entity_names(entities):
    names = set()
    for entity in entities or []:
        if isinstance(entity, str):
            name = entity
        elif isinstance(entity, dict):
            name = entity.get("name") or entity.get("nome")
        else:
            name = getattr(entity, "nome", None) or getattr(entity, "name", None)
        if name:
            names.add(str(name))
    return names


def _enabled_report_refs(raw_reports):
    refs = set()
    if not isinstance(raw_reports, dict):
        return refs
    for entity_name, collection in raw_reports.items():
        items = collection if isinstance(collection, list) else [collection] if isinstance(collection, dict) else []
        for report in items:
            if not isinstance(report, dict) or not report.get("enabled"):
                continue
            report_id = str(report.get("id") or "").strip()
            if report_id:
                refs.add(report_id)
                refs.add(f"{entity_name}:{report_id}")
    return refs


def _destination_catalog(structure, *, entities):
    structure = structure if isinstance(structure, dict) else {}
    advanced = normalize_advanced_pages_config(structure.get("advanced_pages"), strict=False)
    advanced_pages = {page["id"] for page in advanced.get("pages", []) if page.get("enabled")}

    dashboard = normalize_dashboard_config(structure.get("dashboard"))
    dashboards = {"dashboard"} if dashboard.get("enabled") else set()

    entity_names = _entity_names(entities)
    raw_cruds = structure.get("cruds") if isinstance(structure.get("cruds"), dict) else {}
    cruds = set(raw_cruds).intersection(entity_names) if raw_cruds else set(entity_names)

    return {
        "advanced_page": advanced_pages,
        "crud": cruds,
        "dashboard": dashboards,
        "report": _enabled_report_refs(structure.get("reports")),
    }


def validate_workspace_destinations(raw_config, structure, *, entities):
    """Retorna o contrato normalizado quando todos os destinos são semanticamente válidos."""
    config = normalize_workspace_config(raw_config, strict=True)
    catalog = _destination_catalog(structure, entities=entities)

    for workspace in config["workspaces"]:
        for section in workspace["sections"]:
            for item in section["items"]:
                destination = item["destination"]
                kind = destination["kind"]
                ref = destination["ref"]
                context = {
                    "workspace_id": workspace["id"],
                    "section_id": section["id"],
                    "item_id": item["id"],
                }
                if ref not in catalog[kind]:
                    _fail("workspace_destination_not_found", "Destino inexistente, desabilitado ou não navegável.", **context)
                if kind == "crud" and destination.get("operation") != "list":
                    _fail("workspace_destination_not_navigable", "Nesta versão, Workspace navega para a listagem do CRUD.", **context)

    return deepcopy(config)
