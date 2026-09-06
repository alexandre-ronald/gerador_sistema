from django.test import SimpleTestCase

from .advanced_pages import AdvancedPageContractError, normalize_advanced_pages_config
from .advanced_pages_semantics import validate_advanced_pages_semantics


class AdvancedPageActionTransportTests(SimpleTestCase):
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
                    "components": [],
                    "actions": [
                        {
                            "id": "novo_contrato",
                            "kind": "crud",
                            "label": "Novo contrato",
                            "target": {"entity": "Contrato", "operation": "create"},
                            "transport": {
                                "source": "page_context",
                                "source_field": "pk",
                                "target_field": "fornecedor",
                            },
                        }
                    ],
                }
            ],
        }

    def test_contract_preserves_transport(self):
        normalized = normalize_advanced_pages_config(self._config(), strict=True)
        transport = normalized["pages"][0]["actions"][0]["transport"]
        self.assertEqual(transport["target_field"], "fornecedor")

    def test_normalizes_valid_create_transport(self):
        normalized = validate_advanced_pages_semantics(
            self._config(),
            entities_metadata=self._entities(),
        )
        self.assertEqual(
            normalized["pages"][0]["actions"][0]["transport"],
            {"source": "page_context", "source_field": "pk", "target_field": "fornecedor"},
        )

    def test_transport_requires_crud_create(self):
        config = self._config()
        config["pages"][0]["actions"][0]["target"]["operation"] = "list"
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(config, entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "transport_requires_crud_create")

    def test_transport_requires_record_context(self):
        config = self._config()
        config["pages"][0]["context"] = {"kind": "collection", "entity": "Fornecedor"}
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(config, entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "transport_requires_record_context")

    def test_transport_rejects_non_relational_field(self):
        config = self._config()
        config["pages"][0]["actions"][0]["transport"]["target_field"] = "numero"
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(config, entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "transport_target_not_relational")

    def test_transport_rejects_wrong_context_relation(self):
        config = self._config()
        config["pages"][0]["actions"][0]["transport"]["target_field"] = "responsavel"
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(config, entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "transport_context_entity_mismatch")

    def test_transport_rejects_lookup_syntax(self):
        config = self._config()
        config["pages"][0]["actions"][0]["transport"]["target_field"] = "fornecedor__id"
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(config, entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "invalid_transport_target_field")
