from copy import deepcopy

from django.test import SimpleTestCase

from sistema.advanced_pages import AdvancedPageContractError
from sistema.advanced_pages_semantics import validate_advanced_pages_semantics


class AdvancedPagesSemanticTests(SimpleTestCase):
    def metadata(self):
        return [{"name": "Contrato", "fields": [{"name": "numero"}, {"name": "objeto"}]}]

    def config(self):
        return {
            "version": 1,
            "pages": [{
                "id": "contrato_detail",
                "name": "Detalhe do Contrato",
                "slug": "contratos/detalhe",
                "context": {"kind": "record", "entity": "Contrato"},
                "components": [{
                    "id": "numero",
                    "type": "field_summary",
                    "layout": {"x": 0, "y": 0, "w": 6, "h": 1},
                    "binding": {"kind": "field", "ref": "Contrato", "field": "numero"},
                }],
                "actions": [
                    {"id": "editar", "kind": "crud", "target": {"entity": "Contrato", "operation": "update"}},
                    {"id": "aprovar", "kind": "workflow", "target": {"entity": "Contrato", "transition": "aprovar"}},
                    {"id": "relatorio", "kind": "report", "target": {"entity": "Contrato", "report": "contratos_geral"}},
                ],
            }],
        }

    def catalogs(self):
        return {
            "entities_metadata": self.metadata(),
            "workflows": {"Contrato": {"transitions": [{"id": "aprovar"}]}},
            "reports": {"Contrato": [{"id": "contratos_geral"}]},
        }

    def test_accepts_known_semantic_references(self):
        config = validate_advanced_pages_semantics(self.config(), **self.catalogs())
        self.assertEqual(config["pages"][0]["context"]["entity"], "Contrato")

    def test_accepts_real_form_designer_contract_by_entity(self):
        raw = self.config()
        raw["pages"][0]["components"] = [{
            "id": "form_contrato",
            "type": "form",
            "layout": {"x": 0, "y": 0, "w": 12, "h": 2},
            "binding": {"kind": "form", "ref": "Contrato"},
        }]
        config = validate_advanced_pages_semantics(
            raw,
            **self.catalogs(),
            forms={"Contrato": {"title": "Cadastro de Contrato", "sections": [], "fields": []}},
        )
        self.assertEqual(config["pages"][0]["components"][0]["binding"]["ref"], "Contrato")

    def test_rejects_form_without_form_designer_contract(self):
        raw = self.config()
        raw["pages"][0]["components"] = [{
            "id": "form_contrato",
            "type": "form",
            "layout": {"x": 0, "y": 0, "w": 12, "h": 2},
            "binding": {"kind": "form", "ref": "Contrato"},
        }]
        with self.assertRaises(AdvancedPageContractError) as error:
            validate_advanced_pages_semantics(raw, **self.catalogs(), forms={})
        self.assertEqual(error.exception.code, "unknown_form_reference")

    def test_accepts_singular_dashboard_contract(self):
        raw = self.config()
        raw["pages"][0]["components"] = [{
            "id": "dashboard_principal",
            "type": "dashboard",
            "layout": {"x": 0, "y": 0, "w": 12, "h": 3},
            "binding": {"kind": "dashboard", "ref": "main"},
        }]
        config = validate_advanced_pages_semantics(raw, **self.catalogs(), dashboards={"widgets": []})
        self.assertEqual(config["pages"][0]["components"][0]["type"], "dashboard")

    def test_rejects_dashboard_without_dashboard_contract(self):
        raw = self.config()
        raw["pages"][0]["components"] = [{
            "id": "dashboard_principal",
            "type": "dashboard",
            "layout": {"x": 0, "y": 0, "w": 12, "h": 3},
            "binding": {"kind": "dashboard", "ref": "main"},
        }]
        with self.assertRaises(AdvancedPageContractError) as error:
            validate_advanced_pages_semantics(raw, **self.catalogs(), dashboards={})
        self.assertEqual(error.exception.code, "unknown_dashboard_reference")

    def test_rejects_unknown_context_entity(self):
        raw = self.config()
        raw["pages"][0]["context"]["entity"] = "Fantasma"
        with self.assertRaises(AdvancedPageContractError) as error:
            validate_advanced_pages_semantics(raw, **self.catalogs())
        self.assertEqual(error.exception.code, "unknown_entity_reference")

    def test_rejects_unknown_field(self):
        raw = self.config()
        raw["pages"][0]["components"][0]["binding"]["field"] = "inexistente"
        with self.assertRaises(AdvancedPageContractError) as error:
            validate_advanced_pages_semantics(raw, **self.catalogs())
        self.assertEqual(error.exception.code, "unknown_field_reference")

    def test_rejects_unknown_crud_entity(self):
        raw = self.config()
        raw["pages"][0]["actions"][0]["target"]["entity"] = "Fantasma"
        with self.assertRaises(AdvancedPageContractError) as error:
            validate_advanced_pages_semantics(raw, **self.catalogs())
        self.assertEqual(error.exception.code, "unknown_entity_reference")

    def test_rejects_unknown_workflow_transition(self):
        raw = self.config()
        raw["pages"][0]["actions"][1]["target"]["transition"] = "arquivar"
        with self.assertRaises(AdvancedPageContractError) as error:
            validate_advanced_pages_semantics(raw, **self.catalogs())
        self.assertEqual(error.exception.code, "unknown_workflow_transition")

    def test_rejects_unknown_report(self):
        raw = self.config()
        raw["pages"][0]["actions"][2]["target"]["report"] = "fantasma"
        with self.assertRaises(AdvancedPageContractError) as error:
            validate_advanced_pages_semantics(raw, **self.catalogs())
        self.assertEqual(error.exception.code, "unknown_report_reference")

    def test_rejects_workflow_action_without_workflow_catalog(self):
        raw = self.config()
        with self.assertRaises(AdvancedPageContractError) as error:
            validate_advanced_pages_semantics(
                raw,
                entities_metadata=self.metadata(),
                workflows={},
                reports={"Contrato": [{"id": "contratos_geral"}]},
            )
        self.assertEqual(error.exception.code, "unknown_workflow_transition")

    def test_rejects_report_action_without_report_catalog(self):
        raw = self.config()
        with self.assertRaises(AdvancedPageContractError) as error:
            validate_advanced_pages_semantics(
                raw,
                entities_metadata=self.metadata(),
                workflows={"Contrato": {"transitions": [{"id": "aprovar"}]}},
                reports={},
            )
        self.assertEqual(error.exception.code, "unknown_report_reference")

    def test_validation_does_not_mutate_input(self):
        raw = self.config()
        original = deepcopy(raw)
        validate_advanced_pages_semantics(raw, **self.catalogs())
        self.assertEqual(raw, original)
