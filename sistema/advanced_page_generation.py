"""GEN-070.7/070.9 e GEN-071.6 — projeção de páginas avançadas para o gerador Django.

Mantém a fonte de verdade em ``advanced_pages`` e acrescenta apenas metadados de
compilação (nomes Python, referências de modelo, campos, relações, ações e layout).
"""
from copy import deepcopy
import re

from .advanced_pages import normalize_advanced_pages_config


def _runtime_key(component_id):
    value = re.sub(r"[^a-zA-Z0-9_]", "_", str(component_id or ""))
    value = re.sub(r"_+", "_", value).strip("_") or "component"
    if value[0].isdigit():
        value = f"_{value}"
    return f"advanced_component_{value}"


def _field_specs(entity):
    if entity is None:
        return []
    fields = []
    for field in getattr(entity, "campos_geracao", []) or []:
        fields.append({
            "name": field.nome,
            "code": getattr(field, "codigo_nome", field.nome),
            "label": getattr(field, "verbose_nome", None) or getattr(field, "verbose_name", None) or field.nome,
            "type": getattr(field, "tipo", ""),
        })
    return fields


def _field_code(entity, source_name):
    source_name = str(source_name or "").strip()
    if not source_name:
        return ""
    return next((field["code"] for field in _field_specs(entity) if field["name"] == source_name), "")


def _entity_metadata(entity):
    return {
        "app_name": getattr(getattr(entity, "modulo", None), "app_name", "") if entity else "",
        "model_name": getattr(entity, "classe_nome", "") if entity else "",
        "entity_code": getattr(entity, "codigo_nome", "") if entity else "",
    }


def prepare_advanced_pages_generation(raw_config, *, entities):
    config = normalize_advanced_pages_config(raw_config, strict=True)
    entity_map = {entity.nome: entity for entity in entities}
    source_page_map = {page["id"]: page for page in config["pages"] if page.get("enabled") is True}
    pages = []

    for source in config["pages"]:
        if source.get("enabled") is not True:
            continue
        page = deepcopy(source)
        page["url_name"] = f"advanced_page_{page['id']}"
        context = page["context"]
        entity = entity_map.get(context.get("entity"))
        metadata = _entity_metadata(entity)
        page["context_app_name"] = metadata["app_name"]
        page["context_model_name"] = metadata["model_name"]
        page["context_entity_code"] = metadata["entity_code"]
        page["context_fields"] = _field_specs(entity)
        page["requires_pk"] = context.get("kind") == "record"

        action_map = {}
        for action in page["actions"]:
            target = action["target"]
            runtime = {
                "id": action["id"],
                "kind": action["kind"],
                "label": action["label"],
                "target": deepcopy(target),
                "app_name": "",
                "model_name": "",
                "entity_code": "",
                "url_name": "",
                "requires_pk": False,
                "target_context_kind": "",
                "target_context_entity": "",
                "target_context_app_name": "",
                "transport_runtime": None,
            }
            if action["kind"] == "navigate":
                target_page = source_page_map.get(target.get("page"))
                if target_page:
                    target_context = target_page.get("context") or {}
                    target_entity = entity_map.get(target_context.get("entity"))
                    target_meta = _entity_metadata(target_entity)
                    runtime["url_name"] = f"advanced_page_{target_page['id']}"
                    runtime["requires_pk"] = target_context.get("kind") == "record"
                    runtime["target_context_kind"] = target_context.get("kind") or ""
                    runtime["target_context_entity"] = target_context.get("entity") or ""
                    runtime["target_context_app_name"] = target_meta["app_name"]
            else:
                target_entity = entity_map.get(target.get("entity"))
                target_meta = _entity_metadata(target_entity)
                runtime["app_name"] = target_meta["app_name"]
                runtime["model_name"] = target_meta["model_name"]
                runtime["entity_code"] = target_meta["entity_code"]
                if action["kind"] == "crud" and target_entity:
                    operation = target.get("operation")
                    suffix = {"list": "list", "view": "detail", "create": "create", "update": "update", "delete": "delete"}.get(operation, "")
                    if suffix:
                        runtime["url_name"] = f"{target_meta['app_name']}:{target_meta['entity_code']}_{suffix}"
                        runtime["requires_pk"] = operation in {"view", "update", "delete"}
                    transport = action.get("transport") if isinstance(action.get("transport"), dict) else None
                    if operation == "create" and transport:
                        target_field_code = _field_code(target_entity, transport.get("target_field"))
                        if target_field_code:
                            runtime["transport_runtime"] = {
                                "source": "page_context",
                                "source_field": "pk",
                                "target_field": str(transport.get("target_field") or ""),
                                "target_field_code": target_field_code,
                                "query_param": f"_ap_context_{target_field_code}",
                            }
                elif action["kind"] == "workflow" and target_entity:
                    runtime["url_name"] = f"{target_meta['app_name']}:{target_meta['entity_code']}_transition"
                    runtime["requires_pk"] = True
                elif action["kind"] == "report" and target_entity:
                    runtime["url_name"] = f"{target_meta['app_name']}:{target_meta['entity_code']}_report_{target.get('report')}"
            action.update(runtime)
            action_map[action["id"]] = action

        for component in page["components"]:
            layout = component["layout"]
            component["grid_column_start"] = layout["x"] + 1
            component["grid_row_start"] = layout["y"] + 1
            component["runtime_key"] = _runtime_key(component["id"])
            binding = component["binding"]
            binding_entity = entity_map.get(binding.get("ref"))
            if binding.get("kind") == "page_context":
                binding_entity = entity
            binding_meta = _entity_metadata(binding_entity)
            component["binding_app_name"] = binding_meta["app_name"]
            component["binding_model_name"] = binding_meta["model_name"]
            component["binding_entity_code"] = binding_meta["entity_code"]
            component["binding_fields"] = _field_specs(binding_entity)
            component["binding_field"] = next((field for field in component["binding_fields"] if field["name"] == binding.get("field")), None)
            component["runtime_action"] = deepcopy(action_map.get(component.get("action"))) if component.get("action") else None
            component["native_url_name"] = ""
            component["native_requires_pk"] = False
            component["native_operation"] = ""
            component["form_class_name"] = ""
            component["report_id"] = ""
            component["relation_runtime"] = None
            component["aggregate_runtime"] = None

            relation = component.get("config", {}).get("relation") if isinstance(component.get("config"), dict) else None
            if isinstance(relation, dict) and binding_entity:
                target_field_code = _field_code(binding_entity, relation.get("target_field"))
                if target_field_code:
                    component["relation_runtime"] = {
                        "source": "page_context",
                        "source_field": "pk",
                        "target_field": str(relation.get("target_field") or ""),
                        "target_field_code": target_field_code,
                    }
                    aggregate = component.get("config", {}).get("aggregate")
                    if component.get("type") == "metric" and isinstance(aggregate, dict):
                        operation = str(aggregate.get("operation") or "count").strip().lower()
                        field_code = _field_code(binding_entity, aggregate.get("field")) if operation != "count" else ""
                        component["aggregate_runtime"] = {
                            "operation": operation,
                            "field": str(aggregate.get("field") or ""),
                            "field_code": field_code,
                        }

            if component["type"] == "form" and binding_entity:
                same_record = context.get("kind") == "record" and context.get("entity") == binding.get("ref")
                component["native_operation"] = "update" if same_record else "create"
                component["native_requires_pk"] = same_record
                component["form_class_name"] = f"{binding_meta['model_name']}Form"
            elif component["type"] == "report" and binding_entity:
                report_id = str(component.get("config", {}).get("report_id") or "").strip()
                component["report_id"] = report_id
                if report_id:
                    component["native_url_name"] = f"{binding_meta['app_name']}:{binding_meta['entity_code']}_report_{report_id}"
            elif component["type"] == "dashboard":
                component["native_url_name"] = "dashboard"

        pages.append(page)

    # Páginas avançadas de registro não pertencem ao menu principal porque
    # precisam de um PK. O gerador projeta esses entrypoints nas entidades de
    # contexto para que o CRUD consiga alcançá-las sem duplicar configuração.
    for entity_name, entity in entity_map.items():
        entity.advanced_record_pages = [
            {
                "id": page["id"],
                "name": page["name"],
                "url_name": page["url_name"],
            }
            for page in pages
            if page.get("requires_pk")
            and (page.get("context") or {}).get("entity") == entity_name
        ]

    return {"version": config["version"], "pages": pages}
