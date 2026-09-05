from django.test import SimpleTestCase

from sistema.rbac import CRUD_ACTIONS, RBACError, entity_policy, normalize_rbac_config, role_map


class RBACContractTests(SimpleTestCase):
    def setUp(self):
        self.entities = [
            {"name": "Pedido", "label": "Pedido", "fields": []},
            {"name": "Cliente", "label": "Cliente", "fields": []},
        ]
        self.workflows = {
            "Pedido": {
                "enabled": True,
                "state_field": "status",
                "initial_state": "rascunho",
                "states": [
                    {"id": "rascunho", "label": "Rascunho", "final": False, "order": 0},
                    {"id": "aprovado", "label": "Aprovado", "final": True, "order": 1},
                ],
                "transitions": [
                    {"id": "aprovar", "label": "Aprovar", "from": ["rascunho"], "to": "aprovado", "enabled": True, "confirm": False, "confirm_message": "", "order": 0}
                ],
            }
        }

    def valid_config(self):
        return {
            "enabled": True,
            "roles": [
                {"id": "gestor", "label": "Gestor", "description": "Responsável pelas aprovações.", "group": "Gestores", "order": 1},
                {"id": "operador", "label": "Operador", "group": "Operadores", "order": 0},
            ],
            "entities": {
                "Pedido": {
                    "roles": {
                        "gestor": ["delete", "list", "view", "update", "create"],
                        "operador": ["view", "list", "create", "view"],
                    },
                    "transitions": {"aprovar": ["gestor"]},
                }
            },
        }

    def assert_error(self, code, config, *, strict=True):
        with self.assertRaises(RBACError) as ctx:
            normalize_rbac_config(self.entities, self.workflows, config, strict=strict)
        self.assertEqual(ctx.exception.code, code)
        return ctx.exception

    def test_empty_config_preserves_legacy_behavior(self):
        self.assertEqual(
            normalize_rbac_config(self.entities, self.workflows, None),
            {"enabled": False, "roles": [], "entities": {}},
        )

    def test_normalizes_roles_actions_and_transition_permissions(self):
        config = normalize_rbac_config(self.entities, self.workflows, self.valid_config())
        self.assertTrue(config["enabled"])
        self.assertEqual([item["id"] for item in config["roles"]], ["operador", "gestor"])
        self.assertEqual(config["roles"][1]["description"], "Responsável pelas aprovações.")
        self.assertEqual(config["entities"]["Pedido"]["roles"]["gestor"], list(CRUD_ACTIONS))
        self.assertEqual(config["entities"]["Pedido"]["roles"]["operador"], ["list", "view", "create"])
        self.assertEqual(config["entities"]["Pedido"]["transitions"]["aprovar"], ["gestor"])

    def test_role_group_is_derived_from_business_name_when_omitted(self):
        config = self.valid_config()
        config["roles"][0].pop("group")
        normalized = normalize_rbac_config(self.entities, self.workflows, config)
        gestor = next(item for item in normalized["roles"] if item["id"] == "gestor")
        self.assertEqual(gestor["group"], "Gestor")

    def test_legacy_group_is_preserved_when_present(self):
        config = normalize_rbac_config(self.entities, self.workflows, self.valid_config())
        gestor = next(item for item in config["roles"] if item["id"] == "gestor")
        self.assertEqual(gestor["group"], "Gestores")

    def test_rejects_non_boolean_enabled(self):
        config = self.valid_config()
        config["enabled"] = "true"
        self.assert_error("invalid_rbac_enabled", config)

    def test_rejects_duplicate_role(self):
        config = self.valid_config()
        config["roles"].append({"id": "gestor", "label": "Outro", "group": "Outro", "order": 2})
        self.assert_error("duplicate_role_id", config)

    def test_rejects_unsafe_role_id_and_empty_label(self):
        config = self.valid_config()
        config["roles"][0]["id"] = "gestor__root"
        self.assert_error("invalid_role_id", config)
        config = self.valid_config()
        config["roles"][0]["label"] = ""
        self.assert_error("empty_role_label", config)

    def test_rejects_invalid_role_order(self):
        config = self.valid_config()
        config["roles"][0]["order"] = True
        self.assert_error("invalid_role_order", config)

    def test_rejects_unknown_entity_in_strict_mode(self):
        config = self.valid_config()
        config["entities"]["Fantasma"] = {"roles": {}, "transitions": {}}
        error = self.assert_error("unknown_rbac_entity", config)
        self.assertEqual(error.entity, "Fantasma")

    def test_tolerant_mode_skips_unknown_entity(self):
        config = self.valid_config()
        config["entities"]["Fantasma"] = {"roles": {}, "transitions": {}}
        normalized = normalize_rbac_config(self.entities, self.workflows, config, strict=False)
        self.assertNotIn("Fantasma", normalized["entities"])
        self.assertIn("Pedido", normalized["entities"])

    def test_rejects_unknown_role_reference(self):
        config = self.valid_config()
        config["entities"]["Pedido"]["roles"]["auditor"] = ["view"]
        error = self.assert_error("unknown_role_reference", config)
        self.assertEqual(error.role_id, "auditor")

    def test_rejects_unknown_crud_action(self):
        config = self.valid_config()
        config["entities"]["Pedido"]["roles"]["gestor"] = ["list", "export"]
        error = self.assert_error("unknown_crud_action", config)
        self.assertEqual(error.action, "export")

    def test_rejects_unknown_workflow_transition(self):
        config = self.valid_config()
        config["entities"]["Pedido"]["transitions"] = {"publicar": ["gestor"]}
        error = self.assert_error("unknown_transition_reference", config)
        self.assertEqual(error.transition_id, "publicar")

    def test_rejects_unknown_role_in_transition(self):
        config = self.valid_config()
        config["entities"]["Pedido"]["transitions"]["aprovar"] = ["auditor"]
        error = self.assert_error("unknown_role_reference", config)
        self.assertEqual(error.role_id, "auditor")
        self.assertEqual(error.transition_id, "aprovar")

    def test_helpers_return_roles_and_entity_policy(self):
        config = normalize_rbac_config(self.entities, self.workflows, self.valid_config())
        roles = role_map(config)
        self.assertEqual(roles["gestor"]["group"], "Gestores")
        self.assertEqual(roles["gestor"]["description"], "Responsável pelas aprovações.")
        policy = entity_policy(config, "Pedido")
        self.assertIn("gestor", policy["roles"])
        self.assertIsNone(entity_policy(config, "Cliente"))
