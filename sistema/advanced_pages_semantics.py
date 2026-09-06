"""Validação semântica do contrato GEN-070 — Advanced Page Designer.

Mantém a normalização estrutural independente de Django e valida referências contra
metadados explicitamente fornecidos pelos demais Designers.
"""
from copy import deepcopy

from .advanced_pages import AdvancedPageContractError, normalize_advanced_pages_config


def _entity_map(entities_metadata):
    result = {}
    for item in entities_metadata or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("nome") or item.get("class_name") or "").strip()
        if not name:
            continue
        fields = item.get("fields") or item.get("campos") or []
        field_names = set()
        for field in fields:
            if isinstance(field, dict):
                field_name = str(field.get("name") or field.get("nome") or "").strip()
            else:
                field_name = str(field or "").strip()
            if field_name:
                field_names.add(field_name)
        result[name] = {"metadata": deepcopy(item), "fields": field_names}
    return result


def _ids_by_entity(config, *, collection_key):
    result = {}
    if not isinstance(config, dict):
        return result
    for entity_name, value in config.items():
        if not isinstance(value, dict):
            continue
        collection = value.get(collection_key) or []
        result[str(entity_name)] = {
            str(item.get("id") or "").strip()
            for item in collection
            if isinstance(item, dict) and item.get("id")
        }
    return result


def _report_ids(reports):
    result = {}
    if not isinstance(reports, dict):
        return result
    for entity_name, collection in reports.items():
        if not isinstance(collection, list):
            continue
        result[str(entity_name)] = {
            str(item.get("id") or "").strip()
            for item in collection
            if isinstance(item, dict) and item.get("id")
        }
    return result


def _require_entity(entity_name, entities, *, page_id, component_id=None, action_id=None):
    if entity_name not in entities:
        raise AdvancedPageContractError(
            "unknown_entity_reference",
            "Página avançada referencia entidade inexistente.",
            page_id=page_id,
            component_id=component_id,
            action_id=action_id,
        )


def validate_advanced_pages_semantics(
    raw_config,
    *,
    entities_metadata=None,
    workflows=None,
    reports=None,
    forms=None,
    dashboards=None,
):
    """Valida referências externas de páginas avançadas e devolve o contrato normalizado.

    Todos os catálogos são dependências explícitas. A função não consulta banco, models,
    request ou settings, preservando a mesma semântica em Designer, Preview e runtime.
    """
    config = normalize_advanced_pages_config(raw_config, strict=True)
    entities = _entity_map(entities_metadata)
    workflow_ids = _ids_by_entity(workflows, collection_key="transitions")
    report_ids = _report_ids(reports)
    form_ids = _ids_by_entity(forms, collection_key="forms")
    dashboard_ids = _ids_by_entity(dashboards, collection_key="dashboards")

    for page in config["pages"]:
        page_id = page["id"]
        context = page["context"]
        if context["kind"] in ("record", "collection"):
            _require_entity(context["entity"], entities, page_id=page_id)

        for component in page["components"]:
            component_id = component["id"]
            binding = component["binding"]
            kind = binding["kind"]
            ref = binding["ref"]

            if kind in ("entity", "field", "crud"):
                _require_entity(ref, entities, page_id=page_id, component_id=component_id)
            if kind == "field" and binding["field"] not in entities[ref]["fields"]:
                raise AdvancedPageContractError(
                    "unknown_field_reference",
                    "Binding referencia campo inexistente na entidade.",
                    page_id=page_id,
                    component_id=component_id,
                )
            if kind == "workflow":
                _require_entity(ref, entities, page_id=page_id, component_id=component_id)
                if ref not in workflow_ids:
                    raise AdvancedPageContractError("unknown_workflow_reference", "Binding referencia workflow inexistente.", page_id=page_id, component_id=component_id)
            if kind == "report":
                # Binding de relatório usa ref como entidade; report_id fica no config.
                _require_entity(ref, entities, page_id=page_id, component_id=component_id)
                report_id = str(component["config"].get("report_id") or "").strip()
                if not report_id or report_id not in report_ids.get(ref, set()):
                    raise AdvancedPageContractError("unknown_report_reference", "Binding referencia relatório inexistente.", page_id=page_id, component_id=component_id)
            if kind == "form":
                _require_entity(ref, entities, page_id=page_id, component_id=component_id)
                form_id = str(component["config"].get("form_id") or "").strip()
                if forms is not None and (not form_id or form_id not in form_ids.get(ref, set())):
                    raise AdvancedPageContractError("unknown_form_reference", "Binding referencia formulário inexistente.", page_id=page_id, component_id=component_id)
            if kind == "dashboard":
                dashboard_id = str(component["config"].get("dashboard_id") or ref).strip()
                known = {item for values in dashboard_ids.values() for item in values}
                if dashboards is not None and dashboard_id not in known:
                    raise AdvancedPageContractError("unknown_dashboard_reference", "Binding referencia dashboard inexistente.", page_id=page_id, component_id=component_id)

        for action in page["actions"]:
            action_id = action["id"]
            target = action["target"]
            kind = action["kind"]
            if kind == "crud":
                _require_entity(target["entity"], entities, page_id=page_id, action_id=action_id)
            elif kind == "workflow":
                entity = target["entity"]
                _require_entity(entity, entities, page_id=page_id, action_id=action_id)
                if target["transition"] not in workflow_ids.get(entity, set()):
                    raise AdvancedPageContractError("unknown_workflow_transition", "Ação referencia transição inexistente.", page_id=page_id, action_id=action_id)
            elif kind == "report":
                entity = target["entity"]
                _require_entity(entity, entities, page_id=page_id, action_id=action_id)
                if target["report"] not in report_ids.get(entity, set()):
                    raise AdvancedPageContractError("unknown_report_reference", "Ação referencia relatório inexistente.", page_id=page_id, action_id=action_id)

    return config
