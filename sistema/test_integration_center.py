from django.test import SimpleTestCase

from .integration_center import (
    IntegrationCenterError,
    integration_config,
    normalize_integrations_config,
)


class IntegrationCenterContractTests(SimpleTestCase):
    def valid_config(self):
        return {
            "enabled": True,
            "items": [
                {
                    "id": "erp_corporativo",
                    "label": "ERP Corporativo",
                    "base_url": "https://erp.exemplo.gov.br/",
                    "authentication": {"type": "bearer", "env_var": "ERP_API_TOKEN"},
                    "timeout_seconds": 15,
                    "headers": {"Accept": "application/json", "X-Client": "AprovaFlow"},
                    "operations": [
                        {
                            "id": "consultar_fornecedor",
                            "label": "Consultar fornecedor",
                            "method": "get",
                            "path": "/api/fornecedores/{cnpj}",
                            "path_params": ["cnpj"],
                            "query_params": ["ativo"],
                            "body_fields": [],
                        },
                        {
                            "id": "criar_fornecedor",
                            "label": "Criar fornecedor",
                            "method": "POST",
                            "path": "/api/fornecedores",
                            "path_params": [],
                            "query_params": [],
                            "body_fields": ["cnpj", "nome"],
                        },
                    ],
                }
            ],
        }

    def test_empty_config_is_disabled(self):
        self.assertEqual(normalize_integrations_config(None), {"enabled": False, "items": []})

    def test_complete_contract_is_normalized_deterministically(self):
        normalized = normalize_integrations_config(self.valid_config())
        self.assertTrue(normalized["enabled"])
        item = normalized["items"][0]
        self.assertEqual(item["base_url"], "https://erp.exemplo.gov.br")
        self.assertEqual(item["authentication"], {"type": "bearer", "env_var": "ERP_API_TOKEN"})
        self.assertEqual([op["id"] for op in item["operations"]], ["consultar_fornecedor", "criar_fornecedor"])
        self.assertEqual(item["operations"][0]["method"], "GET")

    def test_rejects_invalid_and_duplicate_integration_ids(self):
        config = self.valid_config()
        config["items"][0]["id"] = "ERP-Corporativo"
        with self.assertRaises(IntegrationCenterError) as ctx:
            normalize_integrations_config(config)
        self.assertEqual(ctx.exception.code, "invalid_integration_id")

        config = self.valid_config()
        config["items"].append(dict(config["items"][0]))
        with self.assertRaises(IntegrationCenterError) as ctx:
            normalize_integrations_config(config)
        self.assertEqual(ctx.exception.code, "duplicate_integration_id")

    def test_rejects_insecure_base_url_and_credentials_in_url(self):
        for value in ("ftp://erp.local", "https://user:secret@erp.local", "https://erp.local?a=1", "erp.local"):
            config = self.valid_config()
            config["items"][0]["base_url"] = value
            with self.subTest(value=value), self.assertRaises(IntegrationCenterError) as ctx:
                normalize_integrations_config(config)
            self.assertEqual(ctx.exception.code, "invalid_integration_base_url")

    def test_authentication_modes_require_safe_environment_variables(self):
        modes = [
            {"type": "basic", "username_env_var": "ERP_USER", "password_env_var": "ERP_PASSWORD"},
            {"type": "bearer", "env_var": "ERP_TOKEN"},
            {"type": "api_key", "env_var": "ERP_KEY", "location": "header", "name": "X-API-Key"},
            {"type": "none"},
        ]
        for authentication in modes:
            config = self.valid_config()
            config["items"][0]["authentication"] = authentication
            with self.subTest(authentication=authentication):
                self.assertEqual(normalize_integrations_config(config)["items"][0]["authentication"]["type"], authentication["type"])

        config = self.valid_config()
        config["items"][0]["authentication"] = {"type": "bearer", "env_var": "token-value"}
        with self.assertRaises(IntegrationCenterError) as ctx:
            normalize_integrations_config(config)
        self.assertEqual(ctx.exception.code, "invalid_bearer_env")

    def test_static_authorization_header_is_forbidden(self):
        config = self.valid_config()
        config["items"][0]["headers"]["Authorization"] = "Bearer segredo"
        with self.assertRaises(IntegrationCenterError) as ctx:
            normalize_integrations_config(config)
        self.assertEqual(ctx.exception.code, "forbidden_secret_header")

    def test_timeout_must_be_integer_in_closed_range(self):
        for value in (0, 121, True, 15.5):
            config = self.valid_config()
            config["items"][0]["timeout_seconds"] = value
            with self.subTest(value=value), self.assertRaises(IntegrationCenterError) as ctx:
                normalize_integrations_config(config)
            self.assertEqual(ctx.exception.code, "invalid_integration_timeout")

    def test_rejects_unknown_http_method_and_absolute_operation_path(self):
        config = self.valid_config()
        config["items"][0]["operations"][0]["method"] = "TRACE"
        with self.assertRaises(IntegrationCenterError) as ctx:
            normalize_integrations_config(config)
        self.assertEqual(ctx.exception.code, "unknown_integration_http_method")

        config = self.valid_config()
        config["items"][0]["operations"][0]["path"] = "https://evil.test/api"
        with self.assertRaises(IntegrationCenterError) as ctx:
            normalize_integrations_config(config)
        self.assertEqual(ctx.exception.code, "invalid_integration_operation_path")

    def test_path_placeholders_must_match_declared_path_params(self):
        config = self.valid_config()
        config["items"][0]["operations"][0]["path_params"] = []
        with self.assertRaises(IntegrationCenterError) as ctx:
            normalize_integrations_config(config)
        self.assertEqual(ctx.exception.code, "path_params_mismatch")

        config = self.valid_config()
        config["items"][0]["operations"][0]["path"] = "/api/{cnpj}/{cnpj}"
        config["items"][0]["operations"][0]["path_params"] = ["cnpj"]
        with self.assertRaises(IntegrationCenterError) as ctx:
            normalize_integrations_config(config)
        self.assertEqual(ctx.exception.code, "duplicate_path_placeholder")

    def test_parameter_names_are_unique_across_sources(self):
        config = self.valid_config()
        operation = config["items"][0]["operations"][1]
        operation["query_params"] = ["cnpj"]
        with self.assertRaises(IntegrationCenterError) as ctx:
            normalize_integrations_config(config)
        self.assertEqual(ctx.exception.code, "duplicate_operation_parameter")

    def test_get_and_delete_reject_body_fields(self):
        for method in ("GET", "DELETE"):
            config = self.valid_config()
            operation = config["items"][0]["operations"][0]
            operation["method"] = method
            operation["body_fields"] = ["nome"]
            with self.subTest(method=method), self.assertRaises(IntegrationCenterError) as ctx:
                normalize_integrations_config(config)
            self.assertEqual(ctx.exception.code, "body_not_allowed_for_method")

    def test_duplicate_operation_id_is_rejected(self):
        config = self.valid_config()
        config["items"][0]["operations"][1]["id"] = "consultar_fornecedor"
        with self.assertRaises(IntegrationCenterError) as ctx:
            normalize_integrations_config(config)
        self.assertEqual(ctx.exception.code, "duplicate_integration_operation")

    def test_tolerant_mode_skips_stale_items_and_invalid_global_disables(self):
        config = self.valid_config()
        stale = dict(config["items"][0])
        stale["id"] = "ID INVALIDO"
        config["items"].append(stale)
        normalized = normalize_integrations_config(config, strict=False)
        self.assertEqual(len(normalized["items"]), 1)
        self.assertEqual(normalized["items"][0]["id"], "erp_corporativo")

        self.assertEqual(normalize_integrations_config({"enabled": "sim", "items": []}, strict=False), {"enabled": False, "items": []})

    def test_helper_returns_deep_copy(self):
        config = normalize_integrations_config(self.valid_config())
        item = integration_config(config, "erp_corporativo")
        self.assertEqual(item["id"], "erp_corporativo")
        item["label"] = "Alterado"
        self.assertEqual(config["items"][0]["label"], "ERP Corporativo")
        self.assertIsNone(integration_config(config, "nao_existe"))
