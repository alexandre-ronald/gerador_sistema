"""GEN-070.7 — projeção do contrato de páginas avançadas para o gerador Django.

Mantém a fonte de verdade em ``advanced_pages`` e acrescenta apenas metadados de
compilação (nomes Python, referências de modelo e coordenadas CSS).
"""
from copy import deepcopy

from .advanced_pages import normalize_advanced_pages_config


def prepare_advanced_pages_generation(raw_config, *, entities):
    config = normalize_advanced_pages_config(raw_config, strict=True)
    entity_map = {entity.nome: entity for entity in entities}
    pages = []

    for source in config["pages"]:
        if source.get("enabled") is not True:
            continue
        page = deepcopy(source)
        page["url_name"] = f"advanced_page_{page['id']}"
        context = page["context"]
        entity = entity_map.get(context.get("entity"))
        page["context_app_name"] = getattr(getattr(entity, "modulo", None), "app_name", "") if entity else ""
        page["context_model_name"] = getattr(entity, "classe_nome", "") if entity else ""
        page["context_entity_code"] = getattr(entity, "codigo_nome", "") if entity else ""
        page["requires_pk"] = context.get("kind") == "record"

        for component in page["components"]:
            layout = component["layout"]
            component["grid_column_start"] = layout["x"] + 1
            component["grid_row_start"] = layout["y"] + 1
            binding_entity = entity_map.get(component["binding"].get("ref"))
            component["binding_app_name"] = getattr(getattr(binding_entity, "modulo", None), "app_name", "") if binding_entity else ""
            component["binding_model_name"] = getattr(binding_entity, "classe_nome", "") if binding_entity else ""
            component["binding_entity_code"] = getattr(binding_entity, "codigo_nome", "") if binding_entity else ""

        pages.append(page)

    return {"version": config["version"], "pages": pages}
