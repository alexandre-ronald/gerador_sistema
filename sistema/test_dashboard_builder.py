import json

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from .builder_contracts import normalize_dashboard_config
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .services import GeradorService


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
        self.assertContains(response, "Dashboard Designer 2.0")

    def test_builder_exposes_entity_field_metadata_without_500(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="cadastro")
        entidade = Entidade.objects.create(modulo=modulo, nome="Funcionario")
        Campo.objects.create(entidade=entidade, nome="nome_completo", tipo="CharField", verbose_name="Nome completo")
        Campo.objects.create(entidade=entidade, nome="salario", tipo="DecimalField", verbose_name="Salário", max_digits=12, decimal_places=2)
        response = self.client.get(reverse("sistema:dashboard_builder", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "nome_completo")
        self.assertContains(response, "DecimalField")

    def test_builder_contains_widget_palette_and_grid_engine(self):
        response = self.client.get(reverse("sistema:dashboard_builder", args=[self.sistema.pk]))
        html = response.content.decode()
        self.assertIn('id="canvas"', html)
        self.assertIn('class="btn btn-outline-secondary btn-sm mb-2 add-widget"', html)
        self.assertIn('data-type="metric"', html)
        self.assertIn("function add(type)", html)
        self.assertIn("function reflow(priority=null)", html)
        self.assertIn("const can=", html)
        self.assertIn("x+w.w<=12", html)
        self.assertIn("reflow();", html)

    def test_builder_supports_drag_and_drop_repositioning(self):
        response = self.client.get(reverse("sistema:dashboard_builder", args=[self.sistema.pk]))
        html = response.content.decode()
        # GEN-047 Preview Mode alterna o atributo draggable em runtime:
        # edição => true; preview => false.
        self.assertIn("draggable=\"${previewMode?'false':'true'}\"", html)
        self.assertIn("canvas.ondragstart", html)
        self.assertIn("canvas.ondragover", html)
        self.assertIn("canvas.ondrop", html)
        self.assertIn("if(previewMode){e.preventDefault();return}", html)
        self.assertIn("if(!previewMode&&dragged!==null)e.preventDefault()", html)
        self.assertIn("reflow(w)", html)
        self.assertIn("Math.floor((e.clientX-r.left)/(r.width/12))", html)
        self.assertIn("Math.floor((e.clientY-r.top-16)/80)", html)

    def test_builder_renders_valid_widget_types_object(self):
        response = self.client.get(reverse("sistema:dashboard_builder", args=[self.sistema.pk]))
        html = response.content.decode()
        self.assertIn("const types={", html)
        self.assertIn("'metric':'Indicador'", html)
        self.assertNotIn("const types='metric':", html)

    def test_builder_preserves_analytical_metadata_contract(self):
        response = self.client.get(reverse("sistema:dashboard_builder", args=[self.sistema.pk]))
        html = response.content.decode()
        self.assertIn("Operação", html)
        self.assertIn("Agrupar por", html)
        self.assertIn("group_by_related", html)
        self.assertIn("related_label", html)
        self.assertIn("fields:[]", html)
        self.assertIn("Ordenação", html)

    def test_generated_dashboard_uses_saved_canvas_coordinates(self):
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={"dashboard": {"enabled": True, "title": "Layout", "layout": "12-column", "widgets": [{"id": "a", "type": "metric", "title": "A", "entity": "", "x": 8, "y": 3, "w": 4, "h": 2}]}})
        ctx = GeradorService(self.sistema.pk)._prepare_context()
        widget = ctx["dashboard"]["widgets"][0]
        self.assertEqual(widget["grid_column_start"], 9)
        self.assertEqual(widget["grid_row_start"], 4)

    def test_generated_dashboard_contains_chart_inside_card(self):
        ctx = {"dashboard": {"enabled": True, "title": "Dashboard", "refresh_seconds": 0, "widgets": [{"id": "chart-1", "type": "bar", "title": "Gráfico", "entity": "", "x": 0, "y": 0, "w": 6, "h": 4, "grid_column_start": 1, "grid_row_start": 1}]}}
        html = render_to_string("gerador/snippets/dashboard_html.txt", ctx)
        self.assertIn("display:flex;flex-direction:column", html)
        self.assertIn(".widget-chart{flex:1 1 auto;min-height:0", html)
        self.assertIn(".widget-chart canvas{display:block;width:100%!important;height:100%!important", html)
        self.assertIn("maintainAspectRatio:false", html)

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
