import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .deployment_service import DeploymentService
from .models import Ambiente, DeploymentPlan, ObservabilityEvent, Sistema, VersaoGeracao
from .runtime_agent import RuntimeAgentService


User = get_user_model()


class FakeExecutor:
    def __init__(self, config):
        self.config = config

    def prepare(self):
        return True

    def deploy(self):
        return True


class HealthyRuntimeService:
    def __init__(self, sistema):
        self.sistema = sistema

    def check_environment(self, ambiente):
        return SimpleNamespace(
            online=True,
            status="ok",
            release_observada=str(ambiente.release_atual.numero),
            migrations_pending=0,
        )


class ObservabilityRuntimeDeploymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="obs-owner", password="x")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Observability App", slug="observability-app")
        self.release = VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=1,
            status=VersaoGeracao.STATUS_RELEASED,
            estrutura_json={},
        )
        self.ambiente = Ambiente.objects.create(
            sistema=self.sistema,
            tipo=Ambiente.TIPO_DEVELOPMENT,
            nome="Development",
            url_base="http://127.0.0.1:8001",
            release_atual=self.release,
        )

    @patch("sistema.runtime_agent.urlopen")
    def test_runtime_healthy_events_share_correlation(self, mocked_urlopen):
        payload = {
            "contract": "1.0",
            "status": "ok",
            "system": self.sistema.nome,
            "environment": "DEVELOPMENT",
            "release": "1",
            "database": {"vendor": "sqlite"},
            "migrations": {"pending": 0},
            "uptime_seconds": 10,
        }
        response = MagicMock()
        response.read.return_value = json.dumps(payload).encode()
        response.__enter__.return_value = response
        mocked_urlopen.return_value = response

        RuntimeAgentService(self.sistema).check_environment(self.ambiente)
        events = list(ObservabilityEvent.objects.filter(category=ObservabilityEvent.CATEGORY_RUNTIME).order_by("created_at"))
        self.assertEqual([event.event_name for event in events], ["runtime.check.started", "runtime.check.healthy"])
        self.assertEqual(events[0].correlation_id, events[1].correlation_id)
        self.assertEqual(events[1].ambiente, self.ambiente)

    @patch("sistema.runtime_agent.urlopen", side_effect=OSError("offline"))
    def test_runtime_offline_emits_error_event(self, mocked_urlopen):
        RuntimeAgentService(self.sistema).check_environment(self.ambiente)
        event = ObservabilityEvent.objects.get(event_name="runtime.check.offline")
        self.assertEqual(event.level, ObservabilityEvent.LEVEL_ERROR)
        self.assertEqual(event.context["error"], "offline")

    def test_deployment_success_emits_correlated_lifecycle(self):
        plan = DeploymentPlan.objects.create(
            sistema=self.sistema,
            ambiente=self.ambiente,
            versao=self.release,
            criado_por=self.user,
            status=DeploymentPlan.STATUS_READY,
            executor="local",
            strategy="docker_compose",
            config_snapshot={
                "executor": "local",
                "strategy": "docker_compose",
                "working_directory": "C:/apps/observability",
                "compose_file": "docker-compose.yml",
            },
        )
        DeploymentService(self.sistema).execute_plan(
            plan,
            executor_factory=FakeExecutor,
            runtime_service_factory=HealthyRuntimeService,
        )
        events = list(
            ObservabilityEvent.objects.filter(
                category=ObservabilityEvent.CATEGORY_DEPLOYMENT,
                object_type="DeploymentPlan",
                object_id=str(plan.pk),
            ).order_by("created_at")
        )
        names = [event.event_name for event in events]
        self.assertIn("deployment.started", names)
        self.assertIn("deployment.step.running", names)
        self.assertIn("deployment.step.succeeded", names)
        self.assertIn("deployment.succeeded", names)
        correlations = {event.correlation_id for event in events}
        self.assertEqual(len(correlations), 1)

    @patch("sistema.installer_views.GeradorService.gerar_projeto_completo", side_effect=RuntimeError("generation exploded"))
    def test_generation_failure_emits_started_and_failed(self, mocked_generation):
        self.client.force_login(self.user)
        response = self.client.post(reverse("sistema:processar_geracao_ajax", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 400)
        events = list(ObservabilityEvent.objects.filter(category=ObservabilityEvent.CATEGORY_GENERATION).order_by("created_at"))
        self.assertEqual([event.event_name for event in events], ["generation.started", "generation.failed"])
        self.assertEqual(events[0].correlation_id, events[1].correlation_id)
        self.assertEqual(events[1].usuario, self.user)
