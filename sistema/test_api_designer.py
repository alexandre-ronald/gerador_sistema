from django.test import SimpleTestCase

from .api_designer import APIDesignerError, api_entity_config, normalize_api_config


class APIDesignerContractTests(SimpleTestCase):
    def metadata(self):
        return [
            {
                "name": "Solicitacao",
                "label": "Solicitação",
                "api_eligible": True,
                "workflow_state_field": "status",
                "fields": [
                    {"name": "titulo", "label": "Título", "type": "CharField", "editable": True},
                    {"name": "descricao", "label": "Descrição", "type": "TextField", "editable": True},
                    {"name": "valor", "label": "Valor", "type": "DecimalField", "editable": True},
                    {"name": "status", "label": "Status", "type": "CharField", "editable": True},
                ],
            },
            {
                "name": "Interna",
                "label": "Interna",
                "api_eligible": False,
                "workflow_state_field": "",
                "fields": [{"name": "nome", "label": "Nome", "type": "CharField", "editable": True}],
            },
        ]

    def valid(self):
        return {
            "enabled": True,
            "prefix": "api",
            "version": "v1",
            "authentication": "session_basic",
            "entities": {
                "Solicitacao": {
                    "enabled": True,
                    "endpoint": "solicitacoes",
                    "operations": {"list": True, "retrieve": True, "create": True, "update": True, "partial_update": True, "destroy": False},
                    "fields": ["id", "titulo", "valor", "status"],
                    "read_only_fields": ["id"],
                    "search_fields": ["titulo"],
                    "ordering_fields": ["titulo", "valor"],
                    "default_ordering": ["titulo", "-valor"],
                    "page_size": 25,
                }
            },
        }

    def test_empty_config_preserves_disabled_api(self):
        config = normalize_api_config(False, self.metadata(), None)
        self.assertFalse(config["enabled"])
        self.assertEqual(config["prefix"], "api")
        self.assertEqual(config["version"], "v1")
        self.assertEqual(config["entities"], {})

    def test_normalizes_complete_contract_and_workflow_state_read_only(self):
        config = normalize_api_config(True, self.metadata(), self.valid())
        entity = config["entities"]["Solicitacao"]
        self.assertTrue(config["enabled"])
        self.assertEqual(entity["endpoint"], "solicitacoes")
        self.assertIn("status", entity["read_only_fields"])
        self.assertEqual(entity["default_ordering"], ["titulo", "-valor"])

    def test_rejects_enabled_api_when_system_flag_is_off(self):
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(False, self.metadata(), self.valid())
        self.assertEqual(ctx.exception.code, "system_api_disabled")

    def test_rejects_invalid_prefix_version_and_authentication(self):
        for key, value, code in (
            ("prefix", "../api", "invalid_api_prefix"),
            ("version", "1", "invalid_api_version"),
            ("authentication", "jwt", "invalid_api_authentication"),
        ):
            raw = self.valid(); raw[key] = value
            with self.assertRaises(APIDesignerError) as ctx:
                normalize_api_config(True, self.metadata(), raw)
            self.assertEqual(ctx.exception.code, code)

    def test_rejects_unknown_or_ineligible_entity(self):
        raw = self.valid(); raw["entities"] = {"Fantasma": raw["entities"]["Solicitacao"]}
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, self.metadata(), raw)
        self.assertEqual(ctx.exception.code, "unknown_api_entity")
        raw = self.valid(); raw["entities"] = {"Interna": {**raw["entities"]["Solicitacao"], "endpoint": "internas"}}
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, self.metadata(), raw)
        self.assertEqual(ctx.exception.code, "api_entity_not_eligible")

    def test_rejects_unknown_operation(self):
        raw = self.valid(); raw["entities"]["Solicitacao"]["operations"]["publish"] = True
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, self.metadata(), raw)
        self.assertEqual(ctx.exception.code, "unknown_api_operation")

    def test_rejects_unknown_field_and_empty_fields(self):
        raw = self.valid(); raw["entities"]["Solicitacao"]["fields"] = ["fantasma"]
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, self.metadata(), raw)
        self.assertEqual(ctx.exception.code, "unknown_api_field")
        raw = self.valid(); raw["entities"]["Solicitacao"]["fields"] = []
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, self.metadata(), raw)
        self.assertEqual(ctx.exception.code, "empty_api_fields")

    def test_rejects_read_only_field_not_exposed(self):
        raw = self.valid(); raw["entities"]["Solicitacao"]["read_only_fields"] = ["descricao"]
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, self.metadata(), raw)
        self.assertEqual(ctx.exception.code, "read_only_field_not_exposed")

    def test_rejects_non_text_search_and_search_not_exposed(self):
        raw = self.valid(); raw["entities"]["Solicitacao"]["search_fields"] = ["valor"]
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, self.metadata(), raw)
        self.assertEqual(ctx.exception.code, "invalid_api_search_field")
        raw = self.valid(); raw["entities"]["Solicitacao"]["search_fields"] = ["descricao"]
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, self.metadata(), raw)
        self.assertEqual(ctx.exception.code, "search_field_not_exposed")

    def test_rejects_ordering_not_exposed_or_default_not_allowed(self):
        raw = self.valid(); raw["entities"]["Solicitacao"]["ordering_fields"] = ["descricao"]
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, self.metadata(), raw)
        self.assertEqual(ctx.exception.code, "ordering_field_not_exposed")
        raw = self.valid(); raw["entities"]["Solicitacao"]["default_ordering"] = ["status"]
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, self.metadata(), raw)
        self.assertEqual(ctx.exception.code, "unknown_api_ordering_field")

    def test_rejects_invalid_page_size(self):
        for value in (0, 501, True, "25"):
            raw = self.valid(); raw["entities"]["Solicitacao"]["page_size"] = value
            with self.assertRaises(APIDesignerError) as ctx:
                normalize_api_config(True, self.metadata(), raw)
            self.assertEqual(ctx.exception.code, "invalid_api_page_size")

    def test_rejects_duplicate_endpoint(self):
        metadata = self.metadata() + [{"name": "Pedido", "label": "Pedido", "api_eligible": True, "workflow_state_field": "", "fields": [{"name": "nome", "label": "Nome", "type": "CharField", "editable": True}]}]
        raw = self.valid()
        raw["entities"]["Pedido"] = {"enabled": True, "endpoint": "solicitacoes", "fields": ["id", "nome"], "read_only_fields": ["id"], "search_fields": ["nome"], "ordering_fields": ["nome"], "default_ordering": [], "page_size": 25}
        with self.assertRaises(APIDesignerError) as ctx:
            normalize_api_config(True, metadata, raw)
        self.assertEqual(ctx.exception.code, "duplicate_api_endpoint")

    def test_tolerant_mode_skips_stale_entities(self):
        raw = self.valid(); raw["entities"]["Fantasma"] = raw["entities"].pop("Solicitacao")
        config = normalize_api_config(True, self.metadata(), raw, strict=False)
        self.assertTrue(config["enabled"])
        self.assertEqual(config["entities"], {})

    def test_helper_returns_deep_copy(self):
        config = normalize_api_config(True, self.metadata(), self.valid())
        entity = api_entity_config(config, "Solicitacao")
        entity["endpoint"] = "alterado"
        self.assertEqual(config["entities"]["Solicitacao"]["endpoint"], "solicitacoes")
