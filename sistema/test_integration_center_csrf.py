import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Sistema


class IntegrationCenterCSRFFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="csrf_integracoes", password="x")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Integracoes CSRF", slug="integracoes-csrf")
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

    def test_designer_sets_csrf_cookie_and_save_accepts_ajax_header(self):
        designer_url = reverse("sistema:integration_center", args=[self.sistema.pk])
        save_url = reverse("sistema:salvar_integration_center", args=[self.sistema.pk])

        response = self.client.get(designer_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", self.client.cookies)

        token = self.client.cookies["csrftoken"].value
        payload = {
            "integrations": {
                "enabled": True,
                "items": [{
                    "id": "erp",
                    "label": "ERP",
                    "base_url": "https://erp.example.com",
                    "authentication": {"type": "none"},
                    "timeout_seconds": 15,
                    "headers": {"Accept": "application/json"},
                    "operations": [],
                }],
            }
        }
        response = self.client.post(
            save_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json()["status"], "sucesso")
