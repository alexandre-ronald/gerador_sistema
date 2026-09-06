"""GEN-070.7 — projeção do contrato de páginas avançadas para o gerador Django.

Mantém a fonte de verdade em ``advanced_pages`` e acrescenta apenas metadados de
compilação (nomes Python, referências de modelo, campos, ações e coordenadas CSS).
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
                "entity_code": "",
                "url_name": "",
                "requires_pk": False,
            }
            if action["kind"] == "navigate":
                target_page = source_page_map.get(target.get("page"))
                if target_page:
                    runtime["url_name"] = f"advanced_page_{target_page['id']}"
                    runtime["requires_pk"] = target_page["context"].get("kind") == "record"
            else:
                target_entity = entity_map.get(target.get("entity"))
                target_meta = _entity_metadata(target_entity)
                runtime["app_name"] = target_meta["app_name"]
                runtime["entity_code"] = target_meta["entity_code"]
                if action["kind"] == "crud" and target_entity:
                    operation = target.get("operation")
                    suffix = {"list": "list", "view": "detail", "create": "create", "update": "update", "delete": "delete"}.get(operation, "")
                    if suffix:
                        runtime["url_name"] = f"{target_meta['app_name']}:{target_meta['entity_code']}_{suffix}"
                        runtime["requires_pk"] = operation in {"view", "update", "delete"}
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

        pages.append(page)

    return {"version": config["version"], "pages": pages}
