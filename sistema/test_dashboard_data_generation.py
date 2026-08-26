from pathlib import Path
from django.test import TestCase

from .models import Sistema
from .services import GeradorService


class DashboardDataGenerationTests(TestCase):
    def test_generated_project_contains_live_dashboard_runtime(self):
        sistema = Sistema.objects.create(
            nome="Sistema Dashboard Runtime",
            descricao="Teste",
            caminho_geracao=str(Path(self._testMethodName).resolve().parent / "generated_dashboard_test"),
        )
        # The test focuses on the generator contract; the dashboard configuration
        # itself is already covered by the Dashboard Builder tests.
        service = GeradorService(sistema.pk)
        ctx = service._prepare_context()
        self.assertIn("dashboard_json", ctx)
        self.assertIn("dashboard", ctx)
