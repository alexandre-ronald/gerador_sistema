import os
import tempfile

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .services import GeradorService


class GeneratedReportTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="report_generator", password="x")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sistema = Sistema.objects.create(
            usuario=user,
            nome="Gestão de Contratos",
            slug="gestao-contratos-report",
            caminho_geracao=self.tmp.name,
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="contratos")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Contrato", gerar_crud_views=True)
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=30)
        Campo.objects.create(entidade=self.entidade, nome="fornecedor", tipo="CharField", max_length=120)
        Campo.objects.create(entidade=self.entidade, nome="valor", tipo="DecimalField", max_digits=12, decimal_places=2)
        Campo.objects.create(entidade=self.entidade, nome="vigencia", tipo="DateField")
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "reports": {
                    "Contrato": {
                        "enabled": True,
                        "title": "Relatório de contratos",
                        "description": "Acompanhe contratos cadastrados.",
                        "fields": ["numero", "fornecedor", "valor"],
                        "filters": [
                            {"field": "fornecedor", "type": "contains"},
                            {"field": "valor", "type": "gte"},
                            {"field": "vigencia", "type": "range"},
                        ],
                        "order_by": "-valor",
                    }
                }
            },
        )

    def rendered(self, template):
        service = GeradorService(self.sistema.id)
        ctx = service._prepare_context()
        modulo = ctx["modulos"][0]
        return render_to_string(
            template,
            {
                **ctx,
                "app_name": modulo.app_name,
                "entidades": modulo.entidades_geracao,
                "entidades_crud": modulo.entidades_crud,
                "entidades_api": modulo.entidades_api,
            },
        )

    def test_generated_views_apply_report_filters_and_order(self):
        views = self.rendered("gerador/snippets/views.txt")
        self.assertIn("def contrato_report(request):", views)
        self.assertIn("fornecedor__icontains", views)
        self.assertIn("valor__gte", views)
        self.assertIn("vigencia__gte", views)
        self.assertIn("vigencia__lte", views)
        self.assertIn("queryset = queryset.order_by('-valor')", views)
        self.assertIn("Paginator(queryset, 50)", views)

    def test_generated_urls_expose_report_route(self):
        urls = self.rendered("gerador/snippets/urls_app_v2.txt")
        self.assertIn("contrato/relatorio/", urls)
        self.assertIn("name='contrato_report'", urls)

    def test_report_template_contains_configured_columns_filters_and_print(self):
        service = GeradorService(self.sistema.id)
        ctx = service._prepare_context()
        modulo = ctx["modulos"][0]
        entity = modulo.entidades_geracao[0]
        html = render_to_string(
            "gerador/snippets/html_report.txt",
            {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidade": entity},
        )
        self.assertIn("Relatório de contratos", html)
        self.assertIn("Fornecedor", html)
        self.assertIn("Valor", html)
        self.assertIn("report_fornecedor", html)
        self.assertIn("report_vigencia_from", html)
        self.assertIn("window.print()", html)

    def test_real_generation_creates_report_template_and_route(self):
        logs = GeradorService(self.sistema.id).gerar_projeto_completo()
        report_path = os.path.join(
            self.tmp.name,
            "contratos",
            "templates",
            "contratos",
            "contrato_report.html",
        )
        views_path = os.path.join(self.tmp.name, "contratos", "views.py")
        urls_path = os.path.join(self.tmp.name, "contratos", "urls.py")
        self.assertTrue(os.path.isfile(report_path))
        with open(views_path, encoding="utf-8") as f:
            views = f.read()
        with open(urls_path, encoding="utf-8") as f:
            urls = f.read()
        self.assertIn("def contrato_report(request):", views)
        self.assertIn("contrato/relatorio/", urls)
        self.assertTrue(any("Validação concluída" in item for item in logs))

    def test_disabled_report_does_not_expose_route(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        draft.estrutura_json = {"reports": {"Contrato": {"enabled": False}}}
        draft.save(update_fields=["estrutura_json"])
        urls = self.rendered("gerador/snippets/urls_app_v2.txt")
        self.assertNotIn("contrato/relatorio/", urls)
