from types import SimpleNamespace

from django.test import SimpleTestCase

from .advanced_page_generation import prepare_advanced_pages_generation


class AdvancedPageGenerationTests(SimpleTestCase):
    def entity(self):
        module = SimpleNamespace(app_name="contratos")
        return SimpleNamespace(nome="Contrato", codigo_nome="contrato", classe_nome="Contrato", modulo=module)

    def config(self):
        return {
            "version": 1,
            "pages": [
                {
                    "id": "contrato_detail",
                    "name": "Detalhe do Contrato",
                    "slug": "contratos/detalhe",
                    "enabled": True,
                    "context": {"kind": "record", "entity": "Contrato"},
                    "navigation": {"visible": True, "label": "Detalhe", "icon": "", "group": "Contratos", "order": 0},
                    "components": [
                        {
                            "id": "titulo",
                            "type": "title",
                            "title": "Contrato",
                            "layout": {"x": 2, "y": 3, "w": 6, "h": 1},
                            "binding": {"kind": "none", "ref": "", "field": ""},
                            "action": "",
                            "config": {},
                        }
                    ],
                    "actions": [],
                }
            ],
        }

    def test_prepares_runtime_metadata_without_changing_contract_identity(self):
        result = prepare_advanced_pages_generation(self.config(), entities=[self.entity()])
        page = result["pages"][0]
        self.assertEqual(page["id"], "contrato_detail")
        self.assertEqual(page["url_name"], "advanced_page_contrato_detail")
        self.assertTrue(page["requires_pk"])
        self.assertEqual(page["context_app_name"], "contratos")
        self.assertEqual(page["context_model_name"], "Contrato")
        self.assertEqual(page["components"][0]["grid_column_start"], 3)
        self.assertEqual(page["components"][0]["grid_row_start"], 4)

    def test_navigation_action_projects_target_context_for_runtime_rbac(self):
        raw = self.config()
        raw["pages"].append({
            "id": "central_contratos",
            "name": "Central de Contratos",
            "slug": "contratos/central",
            "enabled": True,
            "context": {"kind": "collection", "entity": "Contrato"},
            "navigation": {"visible": True, "label": "Central", "icon": "", "group": "Contratos", "order": 1},
            "components": [],
            "actions": [],
        })
        raw["pages"][0]["actions"] = [{
            "id": "abrir_central",
            "kind": "navigate",
            "label": "Abrir central",
            "target": {"page": "central_contratos"},
        }]
        result = prepare_advanced_pages_generation(raw, entities=[self.entity()])
        action = result["pages"][0]["actions"][0]
        self.assertEqual(action["url_name"], "advanced_page_central_contratos")
        self.assertEqual(action["target_context_kind"], "collection")
        self.assertEqual(action["target_context_entity"], "Contrato")
        self.assertEqual(action["target_context_app_name"], "contratos")
        self.assertFalse(action["requires_pk"])

    def test_disabled_pages_are_not_emitted_to_runtime(self):
        raw = self.config()
        raw["pages"][0]["enabled"] = False
        result = prepare_advanced_pages_generation(raw, entities=[self.entity()])
        self.assertEqual(result["pages"], [])
