from django.test import SimpleTestCase

from .runtime_contracts import can_component, can_contextual_action, visible_actions


class RelationalRuntimeContractTests(SimpleTestCase):
    def rbac(self):
        return {
            "enabled": True,
            "roles": [
                {"id": "gestor", "label": "Gestor", "description": "", "group": "Gestor", "order": 0},
                {"id": "fornecedor_only", "label": "Fornecedor", "description": "", "group": "Fornecedor", "order": 1},
            ],
            "entities": {
                "Fornecedor": {
                    "roles": {
                        "gestor": ["list", "view"],
                        "fornecedor_only": ["list", "view"],
                    },
                    "transitions": {},
                },
                "Contrato": {
                    "roles": {
                        "gestor": ["list", "view", "create"],
                        "fornecedor_only": [],
                    },
                    "transitions": {},
                },
            },
            "reports": {},
        }

    def page(self):
        return {
            "id": "central_fornecedor",
            "context": {"kind": "record", "entity": "Fornecedor"},
            "actions": [{
                "id": "novo_contrato",
                "kind": "crud",
                "target": {"entity": "Contrato", "operation": "create"},
                "transport": {
                    "source": "page_context",
                    "source_field": "pk",
                    "target_field": "fornecedor",
                },
            }],
            "components": [],
        }

    def related_component(self, component_type="table"):
        return {
            "id": "contratos",
            "type": component_type,
            "binding": {"kind": "entity", "ref": "Contrato", "field": ""},
            "config": {
                "relation": {
                    "source": "page_context",
                    "source_field": "pk",
                    "target_field": "fornecedor",
                }
            },
        }

    def test_related_collection_requires_list_on_target_entity(self):
        page = self.page()
        allowed = can_component(self.rbac(), "gestor", page, self.related_component())
        denied = can_component(self.rbac(), "fornecedor_only", page, self.related_component())
        self.assertTrue(allowed.allowed)
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.code, "related_collection_denied")

    def test_related_metric_uses_collection_permission_not_plain_view(self):
        page = self.page()
        metric = self.related_component("metric")
        self.assertTrue(can_component(self.rbac(), "gestor", page, metric).allowed)
        self.assertFalse(can_component(self.rbac(), "fornecedor_only", page, metric).allowed)

    def test_relation_fails_closed_outside_record_context(self):
        page = self.page()
        page["context"] = {"kind": "collection", "entity": "Fornecedor"}
        decision = can_component(self.rbac(), "gestor", page, self.related_component())
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "relation_requires_record_context")

    def test_relation_rejects_free_lookup_syntax(self):
        component = self.related_component()
        component["config"]["relation"]["target_field"] = "fornecedor__id"
        decision = can_component(self.rbac(), "gestor", self.page(), component)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "invalid_relation_target_field")

    def test_transport_requires_source_page_and_target_create_permission(self):
        page = self.page()
        action = page["actions"][0]
        self.assertTrue(can_contextual_action(self.rbac(), "gestor", page, action).allowed)
        self.assertFalse(can_contextual_action(self.rbac(), "fornecedor_only", page, action).allowed)

    def test_transport_fails_closed_when_contract_is_incomplete(self):
        page = self.page()
        action = dict(page["actions"][0])
        action["transport"] = {"source": "page_context", "source_field": "pk", "target_field": "fornecedor__id"}
        decision = can_contextual_action(self.rbac(), "gestor", page, action)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "invalid_transport_target_field")

    def test_visible_actions_can_enforce_contextual_transport(self):
        page = self.page()
        self.assertEqual(
            [item["id"] for item in visible_actions(self.rbac(), "gestor", page["actions"], page=page)],
            ["novo_contrato"],
        )
        self.assertEqual(visible_actions(self.rbac(), "fornecedor_only", page["actions"], page=page), [])
