import json
import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase

from .dashboard_builder_views import salvar_dashboard
from .models import Sistema, VersaoGeracao
from .services import GeradorService


class GeneratedDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="generated-dashboard", password="senha-forte")

    def test_generation_materializes_saved_dashboard(self):
        with tempfile.TemporaryDirectory() as directory:
            sistema = Sistema.objects.create(usuario=self.user, nome="Sistema Dashboard", caminho_geracao=directory)
            draft = VersaoGeracao.objects.create(
                sistema=sistema,
                numero=0,
                descricao="Rascunho do Dashboard",
                estrutura_json={
                    "dashboard": {
                        "enabled": True,
                        "title": "Indicadores Executivos",
                        "layout": "12-column",
                        "refresh_seconds": 30,
                        "widgets": [
                            {"id": "kpi-1", "type": "metric", "title": "Total", "entity": "", "x": 0, "y": 0, "w": 4, "h": 3, "config": {}}
                        ],
                    }
                },
            )
            GeradorService(sistema.pk).gerar_projeto_completo()
            dashboard_path = os.path.join(directory, "templates", "dashboard.html")
            index_path = os.path.join(directory, "templates", "index.html")
            urls_path = os.path.join(directory, GeradorService(sistema.pk).nome_projeto, "urls.py")
            self.assertTrue(os.path.exists(dashboard_path))
            self.assertIn("Indicadores Executivos", open(dashboard_path, encoding="utf-8").read())
            self.assertIn("Total", open(dashboard_path, encoding="utf-8").read())
            self.assertIn("url 'dashboard'", open(index_path, encoding="utf-8").read())
            self.assertIn("path('dashboard/'", open(urls_path, encoding="utf-8").read())
