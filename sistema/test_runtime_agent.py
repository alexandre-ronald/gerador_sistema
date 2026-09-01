import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Ambiente, RuntimeSnapshot, Sistema, VersaoGeracao
from .runtime_agent import RuntimeAgentService


class RuntimeAgentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="runtime-owner", password="123")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Sistema Runtime")
        self.ambiente = Ambiente.objects.create(
            sistema=self.sistema,
            tipo=Ambiente.TIPO_STAGING,
            nome="Staging",
            url_base="https://staging.example.com",
        )

    def test_requires_http_url(self):
        self.ambiente.url_base = "ftp://example.com"
        service = RuntimeAgentService(self.sistema)
        with self.assertRaises(ValidationError):
            service.check_environment(self.ambiente)

    @patch("sistema.runtime_agent.urlopen")
    def test_persists_online_snapshot(self, mocked_urlopen):
        payload = {
            "contract": "1.0",
            "status": "ok",
            "system": self.sistema.nome,
            "environment": "STAGING",
            "release": "3",
            "database": {"vendor": "postgresql"},
            "migrations": {"pending": 0},
            "uptime_seconds": 120,
        }
        response = MagicMock()
        response.read.return_value = json.dumps(payload).encode()
        response.__enter__.return_value = response
        mocked_urlopen.return_value = response

        snapshot = RuntimeAgentService(self.sistema).check_environment(self.ambiente)
        self.assertTrue(snapshot.online)
        self.assertEqual(snapshot.release_observada, "3")
        self.assertEqual(snapshot.database_vendor, "postgresql")
        self.assertEqual(snapshot.migrations_pending, 0)

    @patch("sistema.runtime_agent.urlopen", side_effect=OSError("offline"))
    def test_connection_failure_is_persisted(self, mocked_urlopen):
        snapshot = RuntimeAgentService(self.sistema).check_environment(self.ambiente)
        self.assertFalse(snapshot.online)
        self.assertIn("offline", snapshot.erro)

    @patch("sistema.runtime_agent.urlopen")
    def test_rejects_incompatible_contract(self, mocked_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({"contract": "9.0", "status": "ok", "system": "X"}).encode()
        response.__enter__.return_value = response
        mocked_urlopen.return_value = response
        snapshot = RuntimeAgentService(self.sistema).check_environment(self.ambiente)
        self.assertFalse(snapshot.online)
        self.assertIn("incompatível", snapshot.erro)

    def test_runtime_route_is_owner_only(self):
        other = get_user_model().objects.create_user(username="other", password="123")
        self.client.force_login(other)
        response = self.client.post(reverse("sistema:check_runtime", args=[self.sistema.id, self.ambiente.id]))
        self.assertEqual(response.status_code, 404)

    def test_environment_page_exposes_runtime_action(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sistema:environment_manager", args=[self.sistema.id]))
        self.assertContains(response, "Runtime Agent")
        self.assertContains(response, "Verificar agora")

    def test_snapshot_is_one_per_environment(self):
        RuntimeSnapshot.objects.create(ambiente=self.ambiente, online=True)
        self.assertEqual(RuntimeSnapshot.objects.filter(ambiente=self.ambiente).count(), 1)

    def test_generated_urls_template_contains_agent_contract(self):
        from django.template.loader import render_to_string
        rendered = render_to_string("gerador/snippets/urls_root_v2.txt", {"sistema": self.sistema, "modulos": []})
        self.assertIn("__djangoforge__/status/", rendered)
        self.assertIn("'contract': '1.0'", rendered)
        self.assertIn("MigrationExecutor", rendered)
