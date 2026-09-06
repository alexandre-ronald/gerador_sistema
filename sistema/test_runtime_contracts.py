from django.test import SimpleTestCase

from .runtime_contracts import (
    can_action,
    can_crud,
    can_report,
    can_workflow_transition,
    visible_actions,
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
