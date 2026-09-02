from django.test import SimpleTestCase

from sistema.workflow import (
    WorkflowError,
    compatible_state_fields,
    normalize_workflow_config,
    normalize_workflows_config,
)


class WorkflowContractTests(SimpleTestCase):
    def setUp(self):
        self.metadata = {
            "name": "Pedido",
            "fields": [
                {"name": "status", "type": "CharField", "editable": True},
                {"name": "descricao", "type": "TextField", "editable": True},
                {"name": "slug_estado", "type": "SlugField", "editable": True},
                {"name": "valor", "type": "DecimalField", "editable": True},
                {"name": "arquivo", "type": "FileField", "editable": True},
                {"name": "cliente", "type": "ForeignKey", "editable": True},
                {"name": "codigo", "type": "CharField", "editable": False},
            ],
        }
        self.valid = {
            "enabled": True,
            "state_field": "status",
            "initial_state": "rascunho",
            "states": [
                {"id": "aprovado", "label": "Aprovado", "final": True, "order": 20},
                {"id": "rascunho", "label": "Rascunho", "final": False, "order": 10},
            ],
            "transitions": [
                {
                    "id": "aprovar",
                    "label": "Aprovar",
                    "from": ["rascunho"],
                    "to": "aprovado",
                    "enabled": True,
                    "confirm": True,
                    "confirm_message": "Confirmar aprovação?",
                    "order": 5,
                }
            ],
        }

    def test_empty_config_preserves_legacy_behavior(self):
        self.assertEqual(
            normalize_workflow_config("Pedido", self.metadata, {}, strict=True),
            {"enabled": False, "state_field": "", "initial_state": "", "states": [], "transitions": []},
        )

    def test_normalizes_and_orders_states_and_transitions(self):
        result = normalize_workflow_config("Pedido", self.metadata, self.valid, strict=True)
        self.assertTrue(result["enabled"])
        self.assertEqual(result["state_field"], "status")
        self.assertEqual(result["initial_state"], "rascunho")
        self.assertEqual([item["id"] for item in result["states"]], ["rascunho", "aprovado"])
        self.assertEqual(result["transitions"][0]["id"], "aprovar")

    def test_compatible_state_fields_only_returns_editable_text_fields(self):
        names = [item["name"] for item in compatible_state_fields(self.metadata)]
        self.assertEqual(names, ["status", "descricao", "slug_estado"])

    def test_rejects_unknown_or_incompatible_state_field(self):
        for field, code in (("inexistente", "unknown_state_field"), ("valor", "incompatible_state_field"), ("cliente", "incompatible_state_field"), ("codigo", "incompatible_state_field")):
            config = {**self.valid, "state_field": field}
            with self.subTest(field=field):
                with self.assertRaises(WorkflowError) as ctx:
                    normalize_workflow_config("Pedido", self.metadata, config, strict=True)
                self.assertEqual(ctx.exception.code, code)

    def test_rejects_duplicate_state_ids_and_unknown_initial_state(self):
        duplicate = {**self.valid, "states": [self.valid["states"][0], self.valid["states"][0]]}
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflow_config("Pedido", self.metadata, duplicate, strict=True)
        self.assertEqual(ctx.exception.code, "duplicate_state_id")

        missing_initial = {**self.valid, "initial_state": "nao_existe"}
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflow_config("Pedido", self.metadata, missing_initial, strict=True)
        self.assertEqual(ctx.exception.code, "unknown_initial_state")

    def test_rejects_transition_with_unknown_origin_or_destination(self):
        bad_origin = {**self.valid, "transitions": [{**self.valid["transitions"][0], "from": ["x"]}]}
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflow_config("Pedido", self.metadata, bad_origin, strict=True)
        self.assertEqual(ctx.exception.code, "unknown_transition_origin")

        bad_destination = {**self.valid, "transitions": [{**self.valid["transitions"][0], "to": "x"}]}
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflow_config("Pedido", self.metadata, bad_destination, strict=True)
        self.assertEqual(ctx.exception.code, "unknown_transition_destination")

    def test_rejects_transition_leaving_final_state(self):
        config = {
            **self.valid,
            "transitions": [
                {
                    **self.valid["transitions"][0],
                    "id": "reabrir",
                    "from": ["aprovado"],
                    "to": "rascunho",
                }
            ],
        }
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflow_config("Pedido", self.metadata, config, strict=True)
        self.assertEqual(ctx.exception.code, "final_state_has_outgoing_transition")

    def test_rejects_duplicate_transition_ids_and_empty_origins(self):
        duplicate = {**self.valid, "transitions": [self.valid["transitions"][0], self.valid["transitions"][0]]}
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflow_config("Pedido", self.metadata, duplicate, strict=True)
        self.assertEqual(ctx.exception.code, "duplicate_transition_id")

        empty = {**self.valid, "transitions": [{**self.valid["transitions"][0], "from": []}]}
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflow_config("Pedido", self.metadata, empty, strict=True)
        self.assertEqual(ctx.exception.code, "empty_transition_from")

    def test_rejects_unsafe_ids_and_invalid_scalar_types(self):
        unsafe = {**self.valid, "states": [{"id": "status__x", "label": "X", "final": False, "order": 0}]}
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflow_config("Pedido", self.metadata, unsafe, strict=True)
        self.assertEqual(ctx.exception.code, "invalid_state_id")

        invalid_bool = {**self.valid, "enabled": "true"}
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflow_config("Pedido", self.metadata, invalid_bool, strict=True)
        self.assertEqual(ctx.exception.code, "invalid_workflow_enabled")

        invalid_order = {**self.valid, "states": [{**self.valid["states"][1], "order": True}, self.valid["states"][0]]}
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflow_config("Pedido", self.metadata, invalid_order, strict=True)
        self.assertEqual(ctx.exception.code, "invalid_state_order")

    def test_confirmation_message_gets_safe_default(self):
        config = {**self.valid, "transitions": [{**self.valid["transitions"][0], "confirm_message": ""}]}
        result = normalize_workflow_config("Pedido", self.metadata, config, strict=True)
        self.assertEqual(result["transitions"][0]["confirm_message"], "Confirmar transição 'Aprovar'?")

    def test_tolerant_mode_drops_unknown_entity_or_stale_state_field(self):
        entities = [self.metadata]
        raw = {"EntidadeRemovida": self.valid, "Pedido": {**self.valid, "state_field": "campo_removido"}}
        self.assertEqual(normalize_workflows_config(entities, raw, strict=False), {"Pedido": {"enabled": False, "state_field": "", "initial_state": "", "states": [], "transitions": []}})

    def test_strict_workflows_reject_unknown_entity(self):
        with self.assertRaises(WorkflowError) as ctx:
            normalize_workflows_config([self.metadata], {"Outra": self.valid}, strict=True)
        self.assertEqual(ctx.exception.code, "unknown_workflow_entity")
