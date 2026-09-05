from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .application_preview import build_preview_shell
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationPreviewAnalyticsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="analytics_preview", password="test123")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Gestão de Contratos",
            interface_nome="Contratos 360",
            tipo_menu="lateral",
            interface_modo="claro",
            interface_densidade="confortavel",
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Contratos")
        self.contrato = Entidade.objects.create(
            modulo=modulo,
            nome="Contrato",
            nome_plural="Contratos",
            gerar_crud_views=True,
        )
        Campo.objects.create(entidade=self.contrato, nome="numero", tipo="CharField", verbose_name="Número")
        Campo.objects.create(entidade=self.contrato, nome="objeto", tipo="CharField", verbose_name="Objeto")
        Campo.objects.create(entidade=self.contrato, nome="valor", tipo="DecimalField", verbose_name="Valor")
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "dashboard": {
                    "enabled": True,
                    "title": "Painel executivo",
                    "layout": "12-column",
                    "refresh_seconds": 60,
                    "widgets": [
                        {
                            "id": "total_contratos",
                            "type": "metric",
                            "title": "Total de contratos",
                            "entity": "Contrato",
                            "x": 0,
                            "y": 0,
                            "w": 4,
                            "h": 3,
                            "config": {"appearance": {"variant": "soft", "show_header": True, "show_border": True, "compact": False}},
                        },
                        {
                            "id": "evolucao",
                            "type": "bar",
                            "title": "Evolução mensal",
                            "entity": "Contrato",
                            "x": 4,
                            "y": 0,
                            "w": 8,
                            "h": 4,
                            "config": {},
                        },
                    ],
                },
                "reports": {
                    "Contrato": [
                        {
                            "id": "contratos_ativos",
                            "enabled": True,
                            "title": "Contratos ativos",
                            "description": "Acompanhamento dos instrumentos vigentes.",
                            "fields": ["numero", "objeto", "valor"],
                            "filters": [{"field": "numero", "type": "contains"}],
                            "order_by": "numero",
                        },
                        {
                            "id": "interno",
                            "enabled": False,
                            "title": "Relatório interno",
                            "fields": ["numero"],
                            "filters": [],
                            "order_by": "",
                        },
                    ]
                },
            },
        )

    def test_projects_dashboard_designer_into_dashboard_preview(self):
        preview = build_preview_shell(self.sistema, page_kind="dashboard")
        page = preview["dashboard_page"]
        self.assertEqual(preview["page_kind"], "dashboard")
        self.assertTrue(page["enabled"])
        self.assertEqual(page["title"], "Painel executivo")
        self.assertEqual(page["refresh_seconds"], 60)
        self.assertEqual(page["widget_count"], 2)
        self.assertEqual(page["widgets"][0]["title"], "Total de contratos")
        self.assertEqual(page["widgets"][0]["kind_label"], "Indicador")
        self.assertEqual(page["widgets"][0]["w"], 4)
        self.assertEqual(page["widgets"][1]["kind_label"], "Barras")
        self.assertTrue(preview["navigation"]["dashboard"]["active"])

    def test_projects_only_enabled_reports(self):
        preview = build_preview_shell(self.sistema, selected_entity_id=self.contrato.pk)
        self.assertEqual([item["id"] for item in preview["reports"]], ["contratos_ativos"])
        report = preview["reports"][0]
        self.assertEqual(report["title"], "Contratos ativos")
        self.assertEqual([field["label"] for field in report["fields_meta"]], ["Número", "Objeto", "Valor"])
        self.assertEqual(report["filters_meta"][0]["label"], "Número")
        self.assertEqual(report["filters_meta"][0]["type_label"], "Contém")
        self.assertEqual(report["rows"][0]["values"], ["Número 01", "Objeto 01", "100"])

    def test_report_selection_is_deterministic(self):
        first = build_preview_shell(
            self.sistema,
            selected_entity_id=self.contrato.pk,
            page_kind="report",
            selected_report_id="contratos_ativos",
        )
        second = build_preview_shell(
            self.sistema,
            selected_entity_id=self.contrato.pk,
            page_kind="report",
            selected_report_id="contratos_ativos",
        )
        self.assertEqual(first["report_page"], second["report_page"])
        self.assertEqual(first["report_page"]["id"], "contratos_ativos")

    def test_dashboard_and_report_views_render(self):
        self.client.force_login(self.user)
        dashboard = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk]),
            {"pagina": "dashboard"},
        )
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'data-preview-page="dashboard"')
        self.assertContains(dashboard, "Painel executivo")
        self.assertContains(dashboard, "Total de contratos")
        self.assertContains(dashboard, "Evolução mensal")

        report = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk]),
            {"entidade": self.contrato.pk, "pagina": "report", "relatorio": "contratos_ativos"},
        )
        self.assertEqual(report.status_code, 200)
        self.assertContains(report, 'data-preview-page="report"')
        self.assertContains(report, "Contratos ativos")
        self.assertContains(report, "Acompanhamento dos instrumentos vigentes.")
        self.assertContains(report, "Número 01")
        self.assertNotContains(report, "Relatório interno")

    def test_preview_still_does_not_persist_parallel_contract(self):
        build_preview_shell(self.sistema, page_kind="dashboard")
        build_preview_shell(
            self.sistema,
            selected_entity_id=self.contrato.pk,
            page_kind="report",
            selected_report_id="contratos_ativos",
        )
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertNotIn("preview", draft.estrutura_json)
        self.assertNotIn("preview_studio", draft.estrutura_json)
