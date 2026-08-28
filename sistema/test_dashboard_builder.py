import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .builder_contracts import normalize_dashboard_config
from .models import Sistema, VersaoGeracao


class DashboardBuilderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="dashboard-user", password="senha-forte")
        self.client.force_login(self.user)
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Dashboard Builder Teste", caminho_geracao="/tmp/projetos")

    def test_contract_normalizes_widgets(self):
        config = normalize_dashboard_config({"widgets": [{"type": "invalid", "w": 99, "h": 0}]})
        self.assertEqual(config["widgets"][0]["type"], "metric")
        self.assertEqual(config["widgets"][0]["w"], 12)
        self.assertEqual(config["widgets"][0]["h"], 1)

    def test_builder_requires_system_owner(self):
        response = self.client.get(reverse("sistema:dashboard_builder", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard Builder")

    def test_builder_exposes_widget_palette_and_canvas_runtime(self):
        response = self.client.get(reverse("sistema:dashboard_builder", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="canvas"')
        self.assertContains(response, 'class="widget-add"')
        self.assertContains(response, 'data-widget-type="metric"')
        self.assertContains(response, "function addWidget(type)")
        self.assertContains(response, "config.widgets.push(newWidget(type))")
        self.assertContains(response, "canvas-empty")

    def test_save_dashboard_creates_draft_version_zero(self):
        payload = {"title": "Indicadores", "refresh_seconds": 30, "widgets": [{"id": "kpi-1", "type": "metric", "title": "Total", "entity": "", "x": 0, "y": 0, "w": 4, "h": 3}]}
        response = self.client.post(reverse("sistema:salvar_dashboard", args=[self.sistema.pk]), data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertEqual(draft.estrutura_json["dashboard"]["title"], "Indicadores")
        self.assertEqual(draft.estrutura_json["dashboard"]["refresh_seconds"], 30)

    def test_save_dashboard_rejects_unknown_entity(self):
        payload = {"widgets": [{"type": "table", "entity": "NaoExiste"}]}
        response = self.client.post(reverse("sistema:salvar_dashboard", args=[self.sistema.pk]), data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
