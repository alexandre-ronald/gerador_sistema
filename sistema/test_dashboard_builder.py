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
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Dashboard Builder Teste",
            caminho_geracao="/tmp/projetos",
        )

    def test_builder_route_is_registered_and_renders_canvas(self):
        response = self.client.get(reverse("sistema:dashboard_builder", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="canvas"')
        self.assertContains(response, 'class="widget-palette-button"')
        self.assertContains(response, 'id="saveDashboardButton"')

    def test_contract_normalizes_widgets(self):
        config = normalize_dashboard_config({"widgets": [{"type": "invalid", "w": 99, "h": 0}]})
        self.assertEqual(config["widgets"][0]["type"], "metric")
        self.assertEqual(config["widgets"][0]["w"], 12)
        self.assertEqual(config["widgets"][0]["h"], 1)

    def test_save_dashboard_route_creates_draft_version_zero(self):
        payload = {
            "title": "Indicadores",
            "refresh_seconds": 30,
            "widgets": [
                {
                    "id": "kpi-1",
                    "type": "metric",
                    "title": "Total",
                    "entity": "",
                    "x": 0,
                    "y": 0,
                    "w": 4,
                    "h": 3,
                }
            ],
        }
        response = self.client.post(
            reverse("sistema:salvar_dashboard", args=[self.sistema.pk]),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "sucesso")
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertEqual(draft.estrutura_json["dashboard"]["title"], "Indicadores")
        self.assertEqual(draft.estrutura_json["dashboard"]["refresh_seconds"], 30)
        self.assertEqual(draft.estrutura_json["dashboard"]["widgets"][0]["w"], 4)
        self.assertEqual(draft.estrutura_json["dashboard"]["widgets"][0]["h"], 3)

    def test_save_dashboard_rejects_unknown_entity(self):
        payload = {"widgets": [{"type": "table", "entity": "NaoExiste"}]}
        response = self.client.post(
            reverse("sistema:salvar_dashboard", args=[self.sistema.pk]),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_grid_places_three_width_four_widgets_on_first_row(self):
        config = normalize_dashboard_config({
            "widgets": [
                {"id": "1", "w": 4, "h": 3},
                {"id": "2", "w": 4, "h": 3},
                {"id": "3", "w": 4, "h": 3},
            ]
        })
        positions = [(w["x"], w["y"]) for w in config["widgets"]]
        self.assertEqual(positions, [(0, 0), (4, 0), (8, 0)])

    def test_grid_moves_widget_to_next_row_when_remaining_space_is_too_small(self):
        config = normalize_dashboard_config({
            "widgets": [
                {"id": "1", "w": 8, "h": 3},
                {"id": "2", "w": 4, "h": 3},
                {"id": "3", "w": 5, "h": 3},
            ]
        })
        positions = [(w["x"], w["y"]) for w in config["widgets"]]
        self.assertEqual(positions, [(0, 0), (8, 0), (0, 3)])

    def test_grid_reflows_after_widget_resize_without_overlap(self):
        config = normalize_dashboard_config({
            "widgets": [
                {"id": "1", "x": 0, "y": 0, "w": 6, "h": 3},
                {"id": "2", "x": 4, "y": 0, "w": 4, "h": 3},
                {"id": "3", "x": 8, "y": 0, "w": 4, "h": 3},
            ]
        })
        widgets = config["widgets"]
        self.assertEqual([(w["x"], w["y"]) for w in widgets], [(0, 0), (6, 0), (0, 3)])

        for index, current in enumerate(widgets):
            for other in widgets[index + 1:]:
                self.assertTrue(
                    current["x"] + current["w"] <= other["x"]
                    or other["x"] + other["w"] <= current["x"]
                    or current["y"] + current["h"] <= other["y"]
                    or other["y"] + other["h"] <= current["y"]
                )

    def test_grid_persists_height_and_width(self):
        config = normalize_dashboard_config({
            "widgets": [{"id": "1", "w": 7, "h": 5}]
        })
        self.assertEqual(config["widgets"][0]["w"], 7)
        self.assertEqual(config["widgets"][0]["h"], 5)
