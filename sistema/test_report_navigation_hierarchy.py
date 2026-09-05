from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .application_preview import build_preview_shell
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .report_designer_views import _entity_metadata, _normalize_report_collection


class ReportNavigationHierarchyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="report_nav", password="test123")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Compras")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Cadastros")
        self.contrato = Entidade.objects.create(modulo=modulo, nome="Contrato", nome_plural="Contratos", gerar_crud_views=True)
        self.fornecedor = Entidade.objects.create(modulo=modulo, nome="Fornecedor", nome_plural="Fornecedores", gerar_crud_views=True)
        Campo.objects.create(entidade=self.contrato, nome="valor", tipo="DecimalField", verbose_name="Valor")
        Campo.objects.create(entidade=self.fornecedor, nome="nome", tipo="CharField", verbose_name="Nome")
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "reports": {
                    "Contrato": [
                        {"id": "valor", "enabled": True, "title": "Valor", "navigation": {"path": ["Contratos"], "label": "Valor"}, "fields": ["valor"], "filters": [], "order_by": ""},
                        {"id": "contratos", "enabled": True, "title": "Contratos", "navigation": {"path": ["Contratos"], "label": "Contratos"}, "fields": ["valor"], "filters": [], "order_by": ""},
                    ],
                    "Fornecedor": [
                        {"id": "fornecedores", "enabled": True, "title": "Fornecedores", "navigation": {"path": ["Fornecedores"], "label": "Fornecedores"}, "fields": ["nome"], "filters": [], "order_by": ""},
                    ],
                }
            },
        )

    def test_old_report_gets_business_navigation_default(self):
        metadata = _entity_metadata(self.contrato)
        result = _normalize_report_collection(
            "Contrato",
            metadata,
            [{"id": "antigo", "enabled": True, "title": "Relatório antigo", "fields": ["valor"], "filters": [], "order_by": ""}],
        )
        self.assertEqual(result[0]["navigation"], {"path": ["Contrato"], "label": "Relatório antigo"})

    def test_preview_projects_group_and_subitems(self):
        preview = build_preview_shell(self.sistema)
        rows = preview["navigation"]["reports"]
        groups = [row["label"] for row in rows if row["kind"] == "group"]
        reports = [(row["depth"], row["label"]) for row in rows if row["kind"] == "report"]
        self.assertEqual(groups, ["Contratos", "Fornecedores"])
        self.assertEqual(reports, [(1, "Contratos"), (1, "Valor"), (1, "Fornecedores")])

    def test_preview_renders_report_hierarchy(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sistema:application_preview", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "preview-nav-group")
        self.assertContains(response, "Contratos")
        self.assertContains(response, "Fornecedores")
        self.assertContains(response, "report-depth-1")

    def test_navigation_identity_is_independent_from_menu_location(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        report = draft.estrutura_json["reports"]["Contrato"][0]
        original_id = report["id"]
        report["navigation"] = {"path": ["Financeiro"], "label": "Valor contratado"}
        draft.save(update_fields=["estrutura_json"])
        preview = build_preview_shell(self.sistema, page_kind="report", selected_report_id=original_id)
        self.assertEqual(preview["report_page"]["id"], original_id)
        self.assertEqual(preview["report_page"]["navigation"]["path"], ["Financeiro"])
