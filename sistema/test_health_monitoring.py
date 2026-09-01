import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .health_monitoring import HealthMonitoringService
from .models import Ambiente, RuntimeCheck, RuntimeSnapshot, Sistema, VersaoGeracao
from .runtime_agent import RuntimeAgentService


class HealthMonitoringTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="health-owner", password="123")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Sistema Health")
        self.release = VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=1,
            status=VersaoGeracao.STATUS_RELEASED,
        )
        self.ambiente = Ambiente.objects.create(
            sistema=self.sistema,
            tipo=Ambiente.TIPO_PRODUCTION,
            nome="Production",
            url_base="https://prod.example.com",
            release_atual=self.release,
        )

    def _state(self):
        return HealthMonitoringService(self.sistema).environment_states()[0]

    def test_unknown_without_snapshot(self):
        self.assertEqual(self._state()["health"], "UNKNOWN")

    def test_healthy_when_runtime_matches_release(self):
        RuntimeSnapshot.objects.create(
            ambiente=self.ambiente,
            online=True,
            status="ok",
            release_observada="1",
            migrations_pending=0,
        )
        state = self._state()
        self.assertEqual(state["health"], "HEALTHY")
        self.assertFalse(state["drift"])

    def test_drift_is_degraded(self):
        RuntimeSnapshot.objects.create(
            ambiente=self.ambiente,
            online=True,
            status="ok",
            release_observada="2",
            migrations_pending=0,
        )
        state = self._state()
        self.assertEqual(state["health"], "DEGRADED")
        self.assertTrue(state["drift"])

    def test_pending_migrations_are_degraded(self):
        RuntimeSnapshot.objects.create(
            ambiente=self.ambiente,
            online=True,
            status="ok",
            release_observada="1",
            migrations_pending=2,
        )
        self.assertEqual(self._state()["health"], "DEGRADED")

    def test_offline_snapshot_is_offline(self):
        RuntimeSnapshot.objects.create(ambiente=self.ambiente, online=False, status="offline")
        self.assertEqual(self._state()["health"], "OFFLINE")

    @patch("sistema.runtime_agent.urlopen")
    def test_runtime_check_creates_history_and_latency(self, mocked_urlopen):
        payload = {
            "contract": "1.0",
            "status": "ok",
            "system": self.sistema.nome,
            "environment": "PRODUCTION",
            "release": "1",
            "database": {"vendor": "sqlite"},
            "migrations": {"pending": 0},
            "uptime_seconds": 30,
        }
        response = MagicMock()
        response.read.return_value = json.dumps(payload).encode()
        response.__enter__.return_value = response
        mocked_urlopen.return_value = response
        RuntimeAgentService(self.sistema).check_environment(self.ambiente)
        check = RuntimeCheck.objects.get(ambiente=self.ambiente)
        self.assertEqual(check.health, "HEALTHY")
        self.assertGreaterEqual(check.latency_ms, 0)

    @patch("sistema.runtime_agent.urlopen", side_effect=OSError("offline"))
    def test_offline_check_is_kept_in_history(self, mocked_urlopen):
        RuntimeAgentService(self.sistema).check_environment(self.ambiente)
        RuntimeAgentService(self.sistema).check_environment(self.ambiente)
        self.assertEqual(RuntimeCheck.objects.filter(ambiente=self.ambiente).count(), 2)
        self.assertTrue(RuntimeCheck.objects.filter(ambiente=self.ambiente, health="OFFLINE").exists())

    def test_health_page_is_owner_only_and_exposes_summary(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sistema:health_monitoring", args=[self.sistema.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Health & Monitoring")
        self.assertContains(response, "UNKNOWN")

        other = get_user_model().objects.create_user(username="health-other", password="123")
        self.client.force_login(other)
        response = self.client.get(reverse("sistema:health_monitoring", args=[self.sistema.id]))
        self.assertEqual(response.status_code, 404)
