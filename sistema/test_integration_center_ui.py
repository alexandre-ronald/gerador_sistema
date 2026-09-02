import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Sistema, VersaoGeracao


class IntegrationCenterUITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="integracoes", password="x")
        self.other = user_model.objects.create_user(username="outro", password="x")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Integracoes", slug="integracoes")
        self.client.force_login(self.user)

    def valid_config(self):
        return {
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
        }

    def test_designer_renders(self):
        response = self.client.get(reverse("sistema:integration_center", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integration Center")
        self.assertContains(response, "Nova integração")
        self.assertContains(response, "Authorization não é permitido")

    def test_save_persists_normalized_integrations_without_touching_other_sections(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"api": {"enabled": False}, "forms": {"X": {"title": "X"}}},
        )
        response = self.client.post(
            reverse("sistema:salvar_integration_center", args=[self.sistema.pk]),
            data=json.dumps({"integrations": self.valid_config()}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "sucesso")
        draft = self.sistema.versoes.get(numero=0).estrutura_json
        self.assertTrue(draft["integrations"]["enabled"])
        self.assertEqual(draft["integrations"]["items"][0]["id"], "erp")
        self.assertEqual(draft["api"], {"enabled": False})
        self.assertIn("X", draft["forms"])

    def test_saved_config_is_loaded_in_designer(self):
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={"integrations": self.valid_config()})
        response = self.client.get(reverse("sistema:integration_center", args=[self.sistema.pk]))
        self.assertContains(response, '"id": "erp"')
        self.assertContains(response, '"env_var": "ERP_API_TOKEN"')

    def test_invalid_contract_returns_structured_400(self):
        config = self.valid_config()
        config["items"][0]["headers"] = {"Authorization": "secret"}
        response = self.client.post(
            reverse("sistema:salvar_integration_center", args=[self.sistema.pk]),
            data=json.dumps({"integrations": config}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "forbidden_secret_header")

    def test_other_user_cannot_open_or_save_system(self):
        other_system = Sistema.objects.create(usuario=self.other, nome="Outro", slug="outro")
        self.assertEqual(self.client.get(reverse("sistema:integration_center", args=[other_system.pk])).status_code, 404)
        response = self.client.post(
            reverse("sistema:salvar_integration_center", args=[other_system.pk]),
            data=json.dumps({"integrations": self.valid_config()}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_workspace_exposes_integration_center(self):
        response = self.client.get(reverse("sistema:lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integration Center")
        self.assertContains(response, reverse("sistema:integration_center", args=[self.sistema.pk]))

    def test_save_requires_integrations_object(self):
        response = self.client.post(
            reverse("sistema:salvar_integration_center", args=[self.sistema.pk]),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "invalid_integrations_config")
