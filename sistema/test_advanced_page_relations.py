from django.test import SimpleTestCase

from .advanced_page_relations import normalize_relation_config
from .advanced_pages import AdvancedPageContractError
from .advanced_pages_semantics import validate_advanced_pages_semantics


class AdvancedPageRelationContractTests(SimpleTestCase):
    def _entities(self):
        return [
            {
                "name": "Fornecedor",
                "fields": [
                    {"name": "razao_social", "type": "CharField", "related_entity": ""},
                ],
            },
            {
                "name": "Contrato",
                "fields": [
                    {"name": "numero", "type": "CharField", "related_entity": ""},
                    {"name": "fornecedor", "type": "ForeignKey", "related_entity": "Fornecedor"},
                    {"name": "responsavel", "type": "ForeignKey", "related_entity": "Usuario"},
                ],
            },
        ]

    def _config(self):
        return {
            "version": 1,
            "pages": [
                {
                    "id": "central_fornecedor",
                    "name": "Central do Fornecedor",
                    "slug": "fornecedores/central",
                    "enabled": True,
                    "context": {"kind": "record", "entity": "Fornecedor"},
                    "navigation": {"visible": False, "label": "", "icon": "", "group": "", "order": 0},
                    "components": [
                        {
                            "id": "contratos",
                            "type": "table",
                            "title": "Contratos do fornecedor",
                            "layout": {"x": 0, "y": 0, "w": 12, "h": 3},
                            "binding": {"kind": "entity", "ref": "Contrato", "field": ""},
                            "action": "",
                            "config": {
                                "relation": {
                                    "source": "page_context",
                                    "source_field": "pk",
                                    "target_field": "fornecedor",
                                }
                            },
                        }
                    ],
                    "actions": [],
                }
            ],
        }

    def test_normalizes_supplier_contract_relation(self):
        normalized = validate_advanced_pages_semantics(
            self._config(),
            entities_metadata=self._entities(),
        )
        relation = normalized["pages"][0]["components"][0]["config"]["relation"]
        self.assertEqual(
            relation,
            {
                "source": "page_context",
                "source_field": "pk",
                "target_field": "fornecedor",
            },
        )

    def test_defaults_safe_source_and_pk(self):
        relation = normalize_relation_config(
            {"target_field": "fornecedor"},
            page_id="central_fornecedor",
            component_id="contratos",
        )
        self.assertEqual(relation["source"], "page_context")
        self.assertEqual(relation["source_field"], "pk")

    def test_relation_requires_record_context(self):
        config = self._config()
        config["pages"][0]["context"] = {"kind": "collection", "entity": "Fornecedor"}
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(config, entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "relation_requires_record_context")

    def test_relation_rejects_unknown_target_field(self):
        config = self._config()
        config["pages"][0]["components"][0]["config"]["relation"]["target_field"] = "fornecedor_inexistente"
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(config, entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "unknown_relation_target_field")

    def test_relation_rejects_non_relational_target_field(self):
        config = self._config()
        config["pages"][0]["components"][0]["config"]["relation"]["target_field"] = "numero"
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(config, entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "relation_target_not_relational")

    def test_relation_rejects_context_entity_mismatch(self):
        config = self._config()
        config["pages"][0]["components"][0]["config"]["relation"]["target_field"] = "responsavel"
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(config, entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "relation_context_entity_mismatch")

    def test_relation_rejects_lookup_syntax(self):
        with self.assertRaises(AdvancedPageContractError) as ctx:
            normalize_relation_config(
                {"target_field": "fornecedor__id"},
                page_id="central_fornecedor",
                component_id="contratos",
            )
        self.assertEqual(ctx.exception.code, "invalid_relation_target_field")
