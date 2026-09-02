import ast
import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Sistema, VersaoGeracao
from .services import GeradorService


class GeneratedIntegrationsTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="integration_gen", password="x")
        self.sistema = Sistema.objects.create(
            usuario=user,
            nome="Integration Runtime",
            slug="integration-runtime",
            caminho_geracao="/tmp/integration-runtime",
        )
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "integrations": {
                    "enabled": True,
                    "items": [{
                        "id": "erp",
                        "label": "ERP",
                        "base_url": "https://erp.example.com",
                        "authentication": {"type": "bearer", "env_var": "ERP_API_TOKEN"},
                        "timeout_seconds": 15,
                        "headers": {"Accept": "application/json"},
                        "operations": [{
                            "id": "consultar_fornecedor",
                            "label": "Consultar fornecedor",
                            "method": "GET",
                            "path": "/fornecedores/{cnpj}",
                            "path_params": ["cnpj"],
                            "query_params": ["ativo"],
                            "body_fields": [],
                        }],
                    }],
                },
            },
        )

    def test_context_materializes_integrations_contract(self):
        ctx = GeradorService(self.sistema.id)._prepare_context()
        self.assertTrue(ctx["integrations"]["enabled"])
        self.assertEqual(ctx["integrations"]["items"][0]["id"], "erp")
        self.assertEqual(ctx["integrations"]["items"][0]["authentication"]["env_var"], "ERP_API_TOKEN")
        self.assertNotIn("secret", ctx["integrations_python"].lower())

    def test_real_generation_writes_runtime_and_httpx_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            self.sistema.caminho_geracao = directory
            self.sistema.save(update_fields=["caminho_geracao"])
            GeradorService(self.sistema.id).gerar_projeto_completo()

            package = os.path.join(directory, "integrations")
            self.assertTrue(os.path.isfile(os.path.join(package, "__init__.py")))
            self.assertTrue(os.path.isfile(os.path.join(package, "config.py")))
            self.assertTrue(os.path.isfile(os.path.join(package, "client.py")))

            with open(os.path.join(directory, "requirements.txt"), encoding="utf-8") as handle:
                self.assertIn("httpx>=0.27,<1", handle.read())

            with open(os.path.join(package, "config.py"), encoding="utf-8") as handle:
                config_source = handle.read()
            self.assertIn("ERP_API_TOKEN", config_source)
            self.assertNotIn("Bearer secret", config_source)
            compile(config_source, "config.py", "exec")

            assignment = next(node for node in ast.parse(config_source).body if isinstance(node, ast.Assign))
            config = ast.literal_eval(assignment.value)
            self.assertTrue(config["enabled"])
            self.assertEqual(config["items"][0]["operations"][0]["id"], "consultar_fornecedor")

            with open(os.path.join(package, "client.py"), encoding="utf-8") as handle:
                client_source = handle.read()
            self.assertIn("os.environ.get", client_source)
            self.assertIn("httpx.request", client_source)
            self.assertIn("IntegrationConfigurationError", client_source)
            self.assertIn("IntegrationRequestError", client_source)
            self.assertIn("IntegrationResponseError", client_source)
            compile(client_source, "client.py", "exec")

    def test_disabled_integrations_preserve_gen055_output_without_httpx(self):
        draft = self.sistema.versoes.get(numero=0)
        draft.estrutura_json["integrations"]["enabled"] = False
        draft.save(update_fields=["estrutura_json"])

        with tempfile.TemporaryDirectory() as directory:
            self.sistema.caminho_geracao = directory
            self.sistema.save(update_fields=["caminho_geracao"])
            GeradorService(self.sistema.id).gerar_projeto_completo()

            self.assertFalse(os.path.exists(os.path.join(directory, "integrations")))
            with open(os.path.join(directory, "requirements.txt"), encoding="utf-8") as handle:
                self.assertNotIn("httpx", handle.read())

    def test_invalid_saved_contract_fails_generation_closed(self):
        draft = self.sistema.versoes.get(numero=0)
        draft.estrutura_json["integrations"]["items"][0]["authentication"] = {
            "type": "bearer",
            "env_var": "token-invalido",
        }
        draft.save(update_fields=["estrutura_json"])

        with self.assertRaises(ValueError):
            GeradorService(self.sistema.id)._prepare_context()
