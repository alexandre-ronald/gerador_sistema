from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .deployment_executor import DeploymentExecutionError
from .deployment_service import DeploymentService
from .models import Ambiente, DeploymentPlan, Sistema, VersaoGeracao


User = get_user_model()


class FakeExecutor:
    def __init__(self, config):
        self.config = config

    def prepare(self):
        return True

    def deploy(self):
        return True


class FailingExecutor(FakeExecutor):
    def deploy(self):
        raise DeploymentExecutionError("command_failed", "Falha controlada no Docker Compose.")


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


class WrongReleaseRuntimeService(HealthyRuntimeService):
    def check_environment(self, ambiente):
        return SimpleNamespace(
            online=True,
            status="ok",
            release_observada="999",
            migrations_pending=0,
        )


class DeploymentRuntimeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="deploy-owner", password="x")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="DeployApp",
            descricao="",
            slug="deployapp",
        )
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
        self.plan = DeploymentPlan.objects.create(
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
                "working_directory": "C:/apps/deployapp",
                "compose_file": "docker-compose.yml",
            },
        )

    def test_execute_plan_reaches_succeeded_after_runtime_confirmation(self):
        result = DeploymentService(self.sistema).execute_plan(
            self.plan,
            executor_factory=FakeExecutor,
            runtime_service_factory=HealthyRuntimeService,
        )
        result.refresh_from_db()
        self.assertEqual(result.status, DeploymentPlan.STATUS_SUCCEEDED)
        self.assertEqual(result.release_observada, "1")
        self.assertIsNotNone(result.iniciado_em)
        self.assertIsNotNone(result.finalizado_em)
        statuses = [(step["name"], step["status"]) for step in result.etapas]
        self.assertIn(("prepare", "SUCCEEDED"), statuses)
        self.assertIn(("deploy", "SUCCEEDED"), statuses)
        self.assertIn(("verify", "SUCCEEDED"), statuses)

    def test_execute_plan_fails_when_executor_fails(self):
        result = DeploymentService(self.sistema).execute_plan(
            self.plan,
            executor_factory=FailingExecutor,
            runtime_service_factory=HealthyRuntimeService,
        )
        result.refresh_from_db()
        self.assertEqual(result.status, DeploymentPlan.STATUS_FAILED)
        self.assertIn("Falha controlada", result.erro)
        self.assertIsNotNone(result.finalizado_em)

    def test_execute_plan_fails_when_runtime_reports_other_release(self):
        result = DeploymentService(self.sistema).execute_plan(
            self.plan,
            executor_factory=FakeExecutor,
            runtime_service_factory=WrongReleaseRuntimeService,
        )
        result.refresh_from_db()
        self.assertEqual(result.status, DeploymentPlan.STATUS_FAILED)
        self.assertEqual(result.release_observada, "999")
        self.assertIn("não corresponde", result.erro)

    def test_execute_plan_rejects_non_ready_plan(self):
        self.plan.status = DeploymentPlan.STATUS_PLANNED
        self.plan.save(update_fields=["status"])
        with self.assertRaises(Exception):
            DeploymentService(self.sistema).execute_plan(
                self.plan,
                executor_factory=FakeExecutor,
                runtime_service_factory=HealthyRuntimeService,
            )

    def test_execute_plan_rejects_ssh_executor(self):
        self.plan.executor = "ssh"
        self.plan.save(update_fields=["executor"])
        with self.assertRaises(ValidationError):
            DeploymentService(self.sistema).execute_plan(
                self.plan,
                executor_factory=FakeExecutor,
                runtime_service_factory=HealthyRuntimeService,
            )
