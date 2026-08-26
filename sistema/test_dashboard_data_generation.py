from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Sistema
from .services import GeradorService


class DashboardDataGenerationTests(TestCase):
    def test_generated_project_contains_live_dashboard_runtime(self):
        user = get_user_model().objects.create_user(username="dashboard-runtime")
        sistema = Sistema.objects.create(
            usuario=user,
            nome="Sistema Dashboard Runtime",
            descricao="Teste",
            caminho_geracao=str(Path(self._testMethodName).resolve().parent / "generated_dashboard_test"),
        )
        service = GeradorService(sistema.pk)
        ctx = service._prepare_context()
        self.assertIn("dashboard_json", ctx)
        self.assertIn("dashboard", ctx)
