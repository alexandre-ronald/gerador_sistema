from django.test import SimpleTestCase

from .runtime_contracts import (
    can_action,
    can_component,
    can_crud,
    can_page,
    can_report,
    can_workflow_transition,
    visible_actions,
    visible_components,
)


class RuntimeContractTests(SimpleTestCase):
    def rbac(self, enabled=True):
        return {
            "enabled": enabled,
            "roles": [
                {"id": "gestor", "label": "Gestor", "description": "", "group": "Gestor", "order": 0},
                {"id": "leitor", "label": "Leitor", "description": "", "group": "Leitor", "order": 1},
            ],
            "entities": {
                "Contrato": {
                    "roles": {"gestor": ["list", "view", "create", "update", "delete"], "leitor": ["list", "view"]},
                    "transitions": {"aprovar": ["gestor"]},
                }
            },
            "reports": {"Contrato": {"geral": ["gestor"]}},
        }

    def page(self, context_kind="record"):
        return {
            "id": "contrato_detail",
            "context": {"kind": context_kind, "entity": "Contrato" if context_kind != "none" else ""},
            "actions": [
                {"id": "editar", "kind": "crud", "target": {"entity": "Contrato", "operation": "update"}},
                {"id": "aprovar", "kind": "workflow", "target": {"entity": "Contrato", "transition": "aprovar"}},
                {"id": "relatorio", "kind": "report", "target": {"entity": "Contrato", "report": "geral"}},
            ],
            "components": [
                {"id": "titulo", "binding": {"kind": "none", "ref": ""}},
                {"id": "numero", "binding": {"kind": "field", "ref": "Contrato", "field": "numero"}},
                {"id": "editar_btn", "action": "editar", "binding": {"kind": "none", "ref": ""}},
                {"id": "aprovar_btn", "action": "aprovar", "binding": {"kind": "workflow", "ref": "Contrato"}},
                {"id": "relatorio_bloco", "binding": {"kind": "report", "ref": "Contrato"}, "config": {"report_id": "geral"}},
            ],
        }

    def test_inactive_policy_does_not_restrict_legacy_runtime(self):
        self.assertTrue(can_crud(self.rbac(False), None, "Contrato", "delete").allowed)

    def test_active_policy_fails_closed_without_role(self):
        decision = can_crud(self.rbac(), None, "Contrato", "view")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "unknown_or_missing_role")

    def test_crud_requires_explicit_grant(self):
        self.assertTrue(can_crud(self.rbac(), "leitor", "Contrato", "view").allowed)
        self.assertFalse(can_crud(self.rbac(), "leitor", "Contrato", "update").allowed)
        self.assertFalse(can_crud(self.rbac(), "leitor", "Fantasma", "view").allowed)

    def test_workflow_requires_transition_grant(self):
        self.assertTrue(can_workflow_transition(self.rbac(), "gestor", "Contrato", "aprovar").allowed)
        self.assertFalse(can_workflow_transition(self.rbac(), "leitor", "Contrato", "aprovar").allowed)
        self.assertFalse(can_workflow_transition(self.rbac(), "gestor", "Contrato", "inexistente").allowed)

    def test_report_requires_explicit_policy(self):
        self.assertTrue(can_report(self.rbac(), "gestor", "Contrato", "geral").allowed)
        self.assertFalse(can_report(self.rbac(), "leitor", "Contrato", "geral").allowed)
        self.assertFalse(can_report(self.rbac(), "gestor", "Contrato", "inexistente").allowed)

    def test_advanced_action_delegates_to_original_capability(self):
        edit = {"kind": "crud", "target": {"entity": "Contrato", "operation": "update"}}
        approve = {"kind": "workflow", "target": {"entity": "Contrato", "transition": "aprovar"}}
        report = {"kind": "report", "target": {"entity": "Contrato", "report": "geral"}}
        self.assertTrue(can_action(self.rbac(), "gestor", edit).allowed)
        self.assertFalse(can_action(self.rbac(), "leitor", edit).allowed)
        self.assertFalse(can_action(self.rbac(), "leitor", approve).allowed)
        self.assertFalse(can_action(self.rbac(), "leitor", report).allowed)

    def test_visible_actions_filters_without_rewriting_permissions(self):
        actions = [
            {"id": "ver", "kind": "crud", "target": {"entity": "Contrato", "operation": "view"}},
            {"id": "editar", "kind": "crud", "target": {"entity": "Contrato", "operation": "update"}},
            {"id": "aprovar", "kind": "workflow", "target": {"entity": "Contrato", "transition": "aprovar"}},
        ]
        self.assertEqual([a["id"] for a in visible_actions(self.rbac(), "leitor", actions)], ["ver"])

    def test_page_access_derives_from_context_capability(self):
        self.assertTrue(can_page(self.rbac(), "leitor", self.page("record")).allowed)
        self.assertTrue(can_page(self.rbac(), "leitor", self.page("collection")).allowed)
        self.assertTrue(can_page(self.rbac(), "leitor", self.page("none")).allowed)
        denied = self.page("record")
        denied["context"]["entity"] = "Fantasma"
        self.assertFalse(can_page(self.rbac(), "leitor", denied).allowed)

    def test_component_with_denied_action_is_hidden(self):
        page = self.page()
        component = next(item for item in page["components"] if item["id"] == "editar_btn")
        self.assertFalse(can_component(self.rbac(), "leitor", page, component).allowed)
        self.assertTrue(can_component(self.rbac(), "gestor", page, component).allowed)

    def test_report_component_uses_report_policy(self):
        page = self.page()
        component = next(item for item in page["components"] if item["id"] == "relatorio_bloco")
        self.assertFalse(can_component(self.rbac(), "leitor", page, component).allowed)
        self.assertTrue(can_component(self.rbac(), "gestor", page, component).allowed)

    def test_component_missing_declared_action_fails_closed(self):
        page = self.page()
        component = {"id": "quebrado", "action": "inexistente", "binding": {"kind": "none", "ref": ""}}
        decision = can_component(self.rbac(), "gestor", page, component)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "missing_component_action")

    def test_visible_components_keeps_read_only_content_for_reader(self):
        visible = visible_components(self.rbac(), "leitor", self.page())
        self.assertEqual([item["id"] for item in visible], ["titulo", "numero"])
