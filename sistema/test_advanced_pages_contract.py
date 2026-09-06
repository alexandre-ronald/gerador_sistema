from django.test import SimpleTestCase

from sistema.advanced_pages import (
    AdvancedPageContractError,
    default_advanced_pages_config,
    normalize_advanced_pages_config,
    page_map,
)


class AdvancedPagesContractTests(SimpleTestCase):
    def valid_config(self):
        return {
            "version": 1,
            "pages": [
                {
                    "id": "contrato_detail",
                    "name": "Detalhe do Contrato",
                    "slug": "contratos/detalhe",
                    "enabled": True,
                    "context": {"kind": "record", "entity": "Contrato"},
                    "navigation": {
                        "visible": True,
                        "label": "Contrato",
                        "icon": "bi-file-earmark-text",
                        "group": "Contratos",
                        "order": 10,
                    },
                    "components": [
                        {
                            "id": "titulo",
                            "type": "title",
                            "title": "Resumo do contrato",
                            "layout": {"x": 0, "y": 0, "w": 12, "h": 1},
                            "binding": {"kind": "page_context"},
                            "config": {},
                        },
                        {
                            "id": "resumo",
                            "type": "record_detail",
                            "title": "Dados principais",
                            "layout": {"x": 0, "y": 1, "w": 8, "h": 2},
                            "binding": {"kind": "entity", "ref": "Contrato"},
                            "config": {"fields": ["numero", "objeto"]},
                        },
                        {
                            "id": "editar",
                            "type": "button",
                            "title": "Editar",
                            "layout": {"x": 8, "y": 1, "w": 4, "h": 1},
                            "binding": {"kind": "page_context"},
                            "action": "editar_contrato",
                            "config": {},
                        },
                    ],
                    "actions": [
                        {
                            "id": "editar_contrato",
                            "kind": "crud",
                            "label": "Editar contrato",
                            "target": {"entity": "Contrato", "operation": "update"},
                        }
                    ],
                }
            ],
        }

    def test_default_contract_is_versioned_and_empty(self):
        self.assertEqual(default_advanced_pages_config(), {"version": 1, "pages": []})

    def test_normalizes_complete_page_contract(self):
        config = normalize_advanced_pages_config(self.valid_config())
        page = config["pages"][0]
        self.assertEqual(page["id"], "contrato_detail")
        self.assertEqual(page["context"], {"kind": "record", "entity": "Contrato"})
        self.assertEqual(page["components"][1]["binding"]["ref"], "Contrato")
        self.assertEqual(page["actions"][0]["target"]["operation"], "update")

    def test_rejects_duplicate_page_ids(self):
        raw = self.valid_config()
        duplicate = dict(raw["pages"][0])
        duplicate["slug"] = "contratos/outro"
        raw["pages"].append(duplicate)
        with self.assertRaises(AdvancedPageContractError) as error:
            normalize_advanced_pages_config(raw)
        self.assertEqual(error.exception.code, "duplicate_page_id")

    def test_rejects_duplicate_slugs(self):
        raw = self.valid_config()
        duplicate = dict(raw["pages"][0])
        duplicate["id"] = "contrato_workspace"
        raw["pages"].append(duplicate)
        with self.assertRaises(AdvancedPageContractError) as error:
            normalize_advanced_pages_config(raw)
        self.assertEqual(error.exception.code, "duplicate_page_slug")

    def test_record_context_requires_entity(self):
        raw = self.valid_config()
        raw["pages"][0]["context"] = {"kind": "record", "entity": ""}
        with self.assertRaises(AdvancedPageContractError) as error:
            normalize_advanced_pages_config(raw)
        self.assertEqual(error.exception.code, "context_entity_required")

    def test_binding_requires_explicit_reference(self):
        raw = self.valid_config()
        raw["pages"][0]["components"][1]["binding"] = {"kind": "entity", "ref": ""}
        with self.assertRaises(AdvancedPageContractError) as error:
            normalize_advanced_pages_config(raw)
        self.assertEqual(error.exception.code, "binding_reference_required")

    def test_layout_rejects_grid_overflow(self):
        raw = self.valid_config()
        raw["pages"][0]["components"][1]["layout"] = {"x": 8, "y": 1, "w": 8, "h": 1}
        with self.assertRaises(AdvancedPageContractError) as error:
            normalize_advanced_pages_config(raw)
        self.assertEqual(error.exception.code, "layout_overflow")

    def test_layout_rejects_collision(self):
        raw = self.valid_config()
        raw["pages"][0]["components"][2]["layout"] = {"x": 7, "y": 1, "w": 4, "h": 1}
        with self.assertRaises(AdvancedPageContractError) as error:
            normalize_advanced_pages_config(raw)
        self.assertEqual(error.exception.code, "layout_collision")

    def test_component_action_must_exist(self):
        raw = self.valid_config()
        raw["pages"][0]["components"][2]["action"] = "acao_inexistente"
        with self.assertRaises(AdvancedPageContractError) as error:
            normalize_advanced_pages_config(raw)
        self.assertEqual(error.exception.code, "unknown_component_action")

    def test_navigation_action_must_point_to_known_page(self):
        raw = self.valid_config()
        raw["pages"][0]["actions"].append(
            {"id": "abrir_workspace", "kind": "navigate", "label": "Workspace", "target": {"page": "workspace"}}
        )
        with self.assertRaises(AdvancedPageContractError) as error:
            normalize_advanced_pages_config(raw)
        self.assertEqual(error.exception.code, "unknown_navigation_page")

    def test_tolerant_mode_discards_invalid_pages(self):
        raw = self.valid_config()
        raw["pages"].append({"id": "quebrada"})
        config = normalize_advanced_pages_config(raw, strict=False)
        self.assertEqual([page["id"] for page in config["pages"]], ["contrato_detail"])

    def test_page_map_returns_copy_by_stable_id(self):
        config = normalize_advanced_pages_config(self.valid_config())
        pages = page_map(config)
        pages["contrato_detail"]["name"] = "Alterado"
        self.assertEqual(config["pages"][0]["name"], "Detalhe do Contrato")