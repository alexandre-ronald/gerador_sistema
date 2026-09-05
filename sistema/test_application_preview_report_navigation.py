from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .application_preview import build_preview_shell
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationPreviewReportNavigationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="report_preview",
            password="test123",
        )
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema de Relatórios",
            tipo_menu="lateral",
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Análises")
        self.operacional = Entidade.objects.create(
            modulo=modulo,
            nome="Operacional",
            nome_plural="Operacionais",
            gerar_crud_views=True,
        )
        self.auditoria = Entidade.objects.create(
            modulo=modulo,
            nome="Auditoria",
            nome_plural="Auditorias",
            gerar_crud_views=False,
        )
        Campo.objects.create(
            entidade=self.operacional,
            nome="nome",
            tipo="CharField",
            verbose_name="Nome",
        )
        Campo.objects.create(
            entidade=self.auditoria,
            nome="evento",
            tipo="CharField",
            verbose_name="Evento",
        )
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "reports": {
                    "Auditoria": [
                        {
                            "id": "auditoria_eventos",
                            "enabled": True,
                            "title": "Eventos de auditoria",
                            "description": "Eventos registrados para conferência.",
                            "fields": ["evento"],
                            "filters": [],
                            "order_by": "evento",
                        }
                    ]
                }
            },
        )

    def test_enabled_reports_are_global_navigation_even_without_crud(self):
        preview = build_preview_shell(self.sistema)
        reports = preview["navigation"]["reports"]
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["label"], "Eventos de auditoria")
        self.assertEqual(reports[0]["entity_id"], self.auditoria.pk)
        self.assertEqual(preview["reports"][0]["entity"], "Auditoria")

    def test_report_can_be_selected_globally_by_report_id(self):
        preview = build_preview_shell(
            self.sistema,
            page_kind="report",
            selected_report_id="auditoria_eventos",
        )
        self.assertEqual(preview["report_page"]["id"], "auditoria_eventos")
        self.assertEqual(preview["report_page"]["entity"], "Auditoria")
        self.assertTrue(preview["navigation"]["reports"][0]["active"])

    def test_preview_renders_report_in_main_navigation(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ">Relatórios<")
        self.assertContains(response, "Eventos de auditoria")
        self.assertContains(
            response,
            f"?entidade={self.auditoria.pk}&pagina=report&relatorio=auditoria_eventos",
        )

    def test_preview_opens_global_report(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk]),
            {"pagina": "report", "relatorio": "auditoria_eventos"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-preview-page="report"')
        self.assertContains(response, "Eventos de auditoria")
        self.assertContains(response, "Eventos registrados para conferência.")
        self.assertContains(response, "Evento 01")
