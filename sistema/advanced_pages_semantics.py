"""Validação semântica do contrato GEN-070/071 — Advanced Page Designer."""
from copy import deepcopy

from .advanced_page_metrics import normalize_related_metric
from .advanced_page_relations import normalize_component_relation
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
        fields_meta = {}
        for field in fields:
            if isinstance(field, dict):
                field_name = str(field.get("name") or field.get("nome") or "").strip()
                field_meta = deepcopy(field)
            else:
                field_name = str(field or "").strip()
                field_meta = {"name": field_name}
            if field_name:
                field_names.add(field_name)
                fields_meta[field_name] = field_meta
        result[name] = {"metadata": deepcopy(item), "fields": field_names, "fields_meta": fields_meta}
    return result


def _ids_by_entity(config, *, collection_key):
    result = {}
    if not isinstance(config, dict):
        return result
    for entity_name, value in config.items():
        if not isinstance(value, dict):
            continue
        collection = value.get(collection_key) or []
        result[str(entity_name)] = {str(item.get("id") or "").strip() for item in collection if isinstance(item, dict) and item.get("id")}
    return result


def _report_ids(reports):
    result = {}
    if isinstance(reports, dict):
        for entity_name, collection in reports.items():
            if isinstance(collection, list):
                result[str(entity_name)] = {str(item.get("id") or "").strip() for item in collection if isinstance(item, dict) and item.get("id")}
    return result


def _form_entities(forms):
    """Form Designer persiste forms como {Entidade: form_config}."""
    if not isinstance(forms, dict):
        return set()
    return {str(entity) for entity, config in forms.items() if isinstance(config, dict)}


def _dashboard_available(dashboard):
    """Dashboard Builder persiste um contrato singular em estrutura_json['dashboard'].

    Dicionário vazio representa ausência explícita do catálogo no Page Designer e,
    portanto, deve falhar fechado. Contratos persistidos reais são dicionários não vazios.
    """
    return isinstance(dashboard, dict) and bool(dashboard)


def _require_entity(entity_name, entities, *, page_id, component_id=None, action_id=None):
    if entity_name not in entities:
        raise AdvancedPageContractError("unknown_entity_reference", "Página avançada referencia entidade inexistente.", page_id=page_id, component_id=component_id, action_id=action_id)


def _validate_record_context(page, entity_name, *, action_id, message):
    context = page.get("context") or {}
    if context.get("kind") != "record" or context.get("entity") != entity_name:
        raise AdvancedPageContractError(
            "incompatible_action_context",
            message,
            page_id=page["id"],
            action_id=action_id,
        )


def _validate_navigation_context(source_page, target_page, *, action_id):
    target_context = target_page.get("context") or {}
    if target_context.get("kind") != "record":
        return
    source_context = source_page.get("context") or {}
    if source_context.get("kind") != "record" or source_context.get("entity") != target_context.get("entity"):
        raise AdvancedPageContractError(
            "incompatible_navigation_context",
            "Navegação para página de registro exige contexto de registro da mesma entidade.",
            page_id=source_page["id"],
            action_id=action_id,
        )


def validate_advanced_pages_semantics(raw_config, *, entities_metadata=None, workflows=None, reports=None, forms=None, dashboards=None):
    config = normalize_advanced_pages_config(raw_config, strict=True)
    entities = _entity_map(entities_metadata)
    workflow_ids = _ids_by_entity(workflows, collection_key="transitions")
    report_ids = _report_ids(reports)
    form_entities = _form_entities(forms)
    dashboard_available = _dashboard_available(dashboards)
    pages_by_id = {page["id"]: page for page in config["pages"]}

    for page in config["pages"]:
        page_id = page["id"]
        context = page["context"]
        if context["kind"] in ("record", "collection"):
            _require_entity(context["entity"], entities, page_id=page_id)

        normalized_components = []
        for component in page["components"]:
            component_id = component["id"]
            binding = component["binding"]
            kind, ref = binding["kind"], binding["ref"]
            if kind in ("entity", "field", "crud"):
                _require_entity(ref, entities, page_id=page_id, component_id=component_id)
            if kind == "field" and binding["field"] not in entities[ref]["fields"]:
                raise AdvancedPageContractError("unknown_field_reference", "Binding referencia campo inexistente na entidade.", page_id=page_id, component_id=component_id)
            if kind == "workflow":
                _require_entity(ref, entities, page_id=page_id, component_id=component_id)
                if ref not in workflow_ids:
                    raise AdvancedPageContractError("unknown_workflow_reference", "Binding referencia workflow inexistente.", page_id=page_id, component_id=component_id)
            if kind == "report":
                _require_entity(ref, entities, page_id=page_id, component_id=component_id)
                report_id = str(component["config"].get("report_id") or "").strip()
                if not report_id or report_id not in report_ids.get(ref, set()):
                    raise AdvancedPageContractError("unknown_report_reference", "Binding referencia relatório inexistente.", page_id=page_id, component_id=component_id)
            if kind == "form":
                _require_entity(ref, entities, page_id=page_id, component_id=component_id)
                if forms is not None and ref not in form_entities:
                    raise AdvancedPageContractError("unknown_form_reference", "Binding referencia formulário inexistente para a entidade.", page_id=page_id, component_id=component_id)
            if kind == "dashboard" and dashboards is not None and not dashboard_available:
                raise AdvancedPageContractError("unknown_dashboard_reference", "Binding referencia dashboard inexistente.", page_id=page_id, component_id=component_id)

            related = normalize_component_relation(component, page, entities)
            normalized_components.append(normalize_related_metric(related, entities, page_id=page_id))

        page["components"] = normalized_components

        for action in page["actions"]:
            action_id, target, kind = action["id"], action["target"], action["kind"]
            if kind == "navigate":
                target_page = pages_by_id.get(target["page"])
                if target_page is not None:
                    _validate_navigation_context(page, target_page, action_id=action_id)
            elif kind == "crud":
                entity = target["entity"]
                _require_entity(entity, entities, page_id=page_id, action_id=action_id)
                if target.get("operation") in {"view", "update", "delete"}:
                    _validate_record_context(
                        page,
                        entity,
                        action_id=action_id,
                        message="Ação CRUD sobre registro exige contexto de registro da mesma entidade.",
                    )
            elif kind == "workflow":
                entity = target["entity"]
                _require_entity(entity, entities, page_id=page_id, action_id=action_id)
                _validate_record_context(
                    page,
                    entity,
                    action_id=action_id,
                    message="Ação de workflow exige contexto de registro da mesma entidade.",
                )
                if target["transition"] not in workflow_ids.get(entity, set()):
                    raise AdvancedPageContractError("unknown_workflow_transition", "Ação referencia transição inexistente.", page_id=page_id, action_id=action_id)
            elif kind == "report":
                entity = target["entity"]
                _require_entity(entity, entities, page_id=page_id, action_id=action_id)
                if target["report"] not in report_ids.get(entity, set()):
                    raise AdvancedPageContractError("unknown_report_reference", "Ação referencia relatório inexistente.", page_id=page_id, action_id=action_id)
    return config
