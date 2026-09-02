from django.test import SimpleTestCase

from sistema.business_rules import (
    BusinessRuleError,
    compatible_operators,
    default_business_rules_config,
    normalize_business_rules_config,
)


class BusinessRulesContractTests(SimpleTestCase):
    def setUp(self):
        self.metadata = {
            "name": "Pedido",
            "fields": [
                {"name": "status", "type": "CharField", "editable": True},
                {"name": "descricao", "type": "TextField", "editable": True},
                {"name": "valor_total", "type": "DecimalField", "editable": True},
                {"name": "quantidade", "type": "IntegerField", "editable": True},
                {"name": "ativo", "type": "BooleanField", "editable": True},
                {"name": "data_solicitacao", "type": "DateField", "editable": True},
                {"name": "data_referencia", "type": "DateField", "editable": True},
                {"name": "cliente", "type": "ForeignKey", "editable": True},
                {"name": "anexos", "type": "ManyToManyField", "editable": True},
                {"name": "codigo_interno", "type": "CharField", "editable": False},
            ],
        }

    def test_default_config_is_empty(self):
        self.assertEqual(default_business_rules_config("Pedido", self.metadata), {"rules": []})

    def test_normalizes_valid_rule_and_orders_by_priority_then_id(self):
        config = {
            "rules": [
                {
                    "id": "z_regra",
                    "name": "Segunda",
                    "enabled": True,
                    "event": "before_save",
                    "priority": 20,
                    "condition_mode": "all",
                    "conditions": [],
                    "actions": [{"type": "set_value", "field": "status", "value": "PENDENTE"}],
                },
                {
                    "id": "a_regra",
                    "name": "Primeira",
                    "enabled": True,
                    "event": "before_create",
                    "priority": 10,
                    "condition_mode": "all",
                    "conditions": [
                        {
                            "field": "valor_total",
                            "operator": "lte",
                            "value_source": "literal",
                            "value": "0.00",
                        }
                    ],
                    "actions": [{"type": "reject", "message": "Valor deve ser maior que zero."}],
                },
            ]
        }

        normalized = normalize_business_rules_config("Pedido", self.metadata, config, strict=True)

        self.assertEqual([rule["id"] for rule in normalized["rules"]], ["a_regra", "z_regra"])
        self.assertEqual(normalized["rules"][0]["conditions"][0]["value"], "0.00")
        self.assertEqual(normalized["rules"][1]["actions"][0]["value"], "PENDENTE")

    def test_rejects_unsafe_names_and_unknown_event(self):
        config = {
            "rules": [
                {
                    "id": "regra__perigosa",
                    "name": "Regra",
                    "event": "before_save",
                    "conditions": [],
                    "actions": [{"type": "reject", "message": "Não."}],
                }
            ]
        }
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, config, strict=True)
        self.assertEqual(ctx.exception.code, "invalid_rule_id")

        config["rules"][0]["id"] = "regra_segura"
        config["rules"][0]["event"] = "after_commit"
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, config, strict=True)
        self.assertEqual(ctx.exception.code, "invalid_event")

    def test_operator_compatibility(self):
        status = self.metadata["fields"][0]
        valor = self.metadata["fields"][2]
        ativo = self.metadata["fields"][4]

        self.assertIn("contains", compatible_operators(status))
        self.assertNotIn("gt", compatible_operators(status))
        self.assertIn("gte", compatible_operators(valor))
        self.assertIn("is_true", compatible_operators(ativo))

        config = {
            "rules": [
                {
                    "id": "comparacao_invalida",
                    "name": "Comparação inválida",
                    "event": "before_save",
                    "conditions": [{"field": "status", "operator": "gt", "value": "A"}],
                    "actions": [{"type": "reject", "message": "Erro"}],
                }
            ]
        }
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, config, strict=True)
        self.assertEqual(ctx.exception.code, "incompatible_operator")

    def test_typed_literals_are_normalized_and_invalid_values_rejected(self):
        config = {
            "rules": [
                {
                    "id": "tipos",
                    "name": "Tipos",
                    "event": "before_save",
                    "conditions": [
                        {"field": "quantidade", "operator": "gte", "value": "10"},
                        {"field": "ativo", "operator": "eq", "value": "sim"},
                        {"field": "data_solicitacao", "operator": "gte", "value": "2026-09-01"},
                    ],
                    "actions": [{"type": "set_value", "field": "valor_total", "value": "12.50"}],
                }
            ]
        }

        normalized = normalize_business_rules_config("Pedido", self.metadata, config, strict=True)
        conditions = normalized["rules"][0]["conditions"]
        self.assertEqual(conditions[0]["value"], 10)
        self.assertIs(conditions[1]["value"], True)
        self.assertEqual(conditions[2]["value"], "2026-09-01")
        self.assertEqual(normalized["rules"][0]["actions"][0]["value"], "12.50")

        config["rules"][0]["conditions"][0]["value"] = "dez"
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, config, strict=True)
        self.assertEqual(ctx.exception.code, "invalid_literal")

    def test_field_value_source_and_copy_value_are_supported(self):
        config = {
            "rules": [
                {
                    "id": "copiar_data",
                    "name": "Copiar data",
                    "event": "before_update",
                    "condition_mode": "any",
                    "conditions": [
                        {
                            "field": "data_referencia",
                            "operator": "lt",
                            "value_source": "field",
                            "value": "data_solicitacao",
                        }
                    ],
                    "actions": [
                        {"type": "copy_value", "field": "data_referencia", "source_field": "data_solicitacao"}
                    ],
                }
            ]
        }

        normalized = normalize_business_rules_config("Pedido", self.metadata, config, strict=True)
        rule = normalized["rules"][0]
        self.assertEqual(rule["condition_mode"], "any")
        self.assertEqual(rule["conditions"][0]["value_source"], "field")
        self.assertEqual(rule["actions"][0]["source_field"], "data_solicitacao")

    def test_reject_requires_message_and_rule_requires_action(self):
        base_rule = {
            "id": "validar",
            "name": "Validar",
            "event": "before_save",
            "conditions": [],
            "actions": [{"type": "reject", "message": ""}],
        }
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, {"rules": [base_rule]}, strict=True)
        self.assertEqual(ctx.exception.code, "empty_reject_message")

        base_rule["actions"] = []
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, {"rules": [base_rule]}, strict=True)
        self.assertEqual(ctx.exception.code, "empty_actions")

    def test_non_assignable_and_many_to_many_fields_are_rejected(self):
        config = {
            "rules": [
                {
                    "id": "alterar_interno",
                    "name": "Alterar interno",
                    "event": "before_save",
                    "conditions": [],
                    "actions": [{"type": "set_value", "field": "codigo_interno", "value": "X"}],
                }
            ]
        }
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, config, strict=True)
        self.assertEqual(ctx.exception.code, "non_assignable_field")

        config["rules"][0]["actions"] = [{"type": "copy_value", "field": "status", "source_field": "anexos"}]
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, config, strict=True)
        self.assertEqual(ctx.exception.code, "incompatible_source_field")

    def test_duplicate_ids_and_invalid_priority_are_rejected(self):
        rule = {
            "id": "regra",
            "name": "Regra",
            "event": "before_save",
            "priority": 0,
            "conditions": [],
            "actions": [{"type": "reject", "message": "Erro"}],
        }
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, {"rules": [rule, dict(rule)]}, strict=True)
        self.assertEqual(ctx.exception.code, "duplicate_rule_id")

        rule["priority"] = 10001
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, {"rules": [rule]}, strict=True)
        self.assertEqual(ctx.exception.code, "invalid_priority")

    def test_tolerant_mode_drops_stale_references_but_strict_rejects(self):
        config = {
            "rules": [
                {
                    "id": "regra_antiga",
                    "name": "Regra antiga",
                    "event": "before_save",
                    "conditions": [{"field": "campo_removido", "operator": "eq", "value": "X"}],
                    "actions": [{"type": "set_value", "field": "status", "value": "ATIVO"}],
                },
                {
                    "id": "acao_antiga",
                    "name": "Ação antiga",
                    "event": "before_save",
                    "conditions": [],
                    "actions": [{"type": "set_value", "field": "campo_removido", "value": "X"}],
                },
            ]
        }

        tolerant = normalize_business_rules_config("Pedido", self.metadata, config, strict=False)
        self.assertEqual(len(tolerant["rules"]), 1)
        self.assertEqual(tolerant["rules"][0]["id"], "regra_antiga")
        self.assertEqual(tolerant["rules"][0]["conditions"], [])

        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", self.metadata, config, strict=True)
        self.assertEqual(ctx.exception.code, "unknown_condition_field")

    def test_unknown_entity_metadata_is_rejected(self):
        metadata = dict(self.metadata)
        metadata["name"] = "Cliente"
        with self.assertRaises(BusinessRuleError) as ctx:
            normalize_business_rules_config("Pedido", metadata, {}, strict=True)
        self.assertEqual(ctx.exception.code, "unknown_entity")
