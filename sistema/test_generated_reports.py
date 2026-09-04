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
                    "Contrato": [
                        {
                            "id": "por_fornecedor",
                            "enabled": True,
                            "title": "Contratos por fornecedor",
                            "description": "Acompanhe contratos por fornecedor.",
                            "fields": ["numero", "fornecedor", "valor"],
                            "filters": [{"field": "fornecedor", "type": "contains"}],
                            "order_by": "fornecedor",
                        },
                        {
                            "id": "maiores_valores",
                            "enabled": True,
                            "title": "Contratos de maior valor",
                            "description": "Liste contratos por valor.",
                            "fields": ["numero", "valor", "vigencia"],
                            "filters": [
                                {"field": "valor", "type": "gte"},
                                {"field": "vigencia", "type": "range"},
                            ],
                            "order_by": "-valor",
                        },
                    ]
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

    def test_generated_views_apply_each_report_configuration(self):
        views = self.rendered("gerador/snippets/views.txt")
        self.assertIn("def contrato_report_por_fornecedor(request):", views)
        self.assertIn("def contrato_report_maiores_valores(request):", views)
        self.assertIn("fornecedor__icontains", views)
        self.assertIn("valor__gte", views)
        self.assertIn("vigencia__gte", views)
        self.assertIn("vigencia__lte", views)
        self.assertIn("queryset = queryset.order_by('-valor')", views)
        self.assertIn("'report_id': 'por_fornecedor'", views)
        self.assertIn("'report_id': 'maiores_valores'", views)

    def test_generated_urls_expose_all_report_routes(self):
        urls = self.rendered("gerador/snippets/urls_app_v2.txt")
        self.assertIn("contrato/relatorios/por_fornecedor/", urls)
        self.assertIn("contrato/relatorios/maiores_valores/", urls)
        self.assertIn("name='contrato_report_por_fornecedor'", urls)
        self.assertIn("name='contrato_report_maiores_valores'", urls)

    def test_generated_navigation_exposes_report_links(self):
        navigation = self.rendered("gerador/snippets/navigation_context.txt")
        self.assertIn('"label": "Contratos por fornecedor"', navigation)
        self.assertIn('"label": "Contratos de maior valor"', navigation)
        self.assertIn('"url_name": "contratos:contrato_report_por_fornecedor"', navigation)
        self.assertIn('"url_name": "contratos:contrato_report_maiores_valores"', navigation)
        self.assertIn('"is_report": True', navigation)

    def test_report_template_contains_all_report_variants(self):
        service = GeradorService(self.sistema.id)
        ctx = service._prepare_context()
        modulo = ctx["modulos"][0]
        entity = modulo.entidades_geracao[0]
        html = render_to_string(
            "gerador/snippets/html_report.txt",
            {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidade": entity},
        )
        self.assertIn("Contratos por fornecedor", html)
        self.assertIn("Contratos de maior valor", html)
        self.assertIn("report_id == 'por_fornecedor'", html)
        self.assertIn("report_id == 'maiores_valores'", html)
        self.assertIn("window.print()", html)

    def test_real_generation_creates_report_template_routes_and_navigation(self):
        logs = GeradorService(self.sistema.id).gerar_projeto_completo()
        report_path = os.path.join(self.tmp.name, "contratos", "templates", "contratos", "contrato_report.html")
        views_path = os.path.join(self.tmp.name, "contratos", "views.py")
        urls_path = os.path.join(self.tmp.name, "contratos", "urls.py")
        navigation_path = os.path.join(self.tmp.name, "gestao_de_contratos", "context_processors.py")
        self.assertTrue(os.path.isfile(report_path))
        with open(views_path, encoding="utf-8") as f:
            views = f.read()
        with open(urls_path, encoding="utf-8") as f:
            urls = f.read()
        with open(navigation_path, encoding="utf-8") as f:
            navigation = f.read()
        self.assertIn("def contrato_report_por_fornecedor(request):", views)
        self.assertIn("def contrato_report_maiores_valores(request):", views)
        self.assertIn("contrato/relatorios/por_fornecedor/", urls)
        self.assertIn("contrato/relatorios/maiores_valores/", urls)
        self.assertIn("Contratos por fornecedor", navigation)
        self.assertIn("Contratos de maior valor", navigation)
        self.assertTrue(any("Validação concluída" in item for item in logs))

    def test_disabled_reports_do_not_expose_routes_or_navigation(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        draft.estrutura_json = {"reports": {"Contrato": [{"id": "inativo", "enabled": False}]}}
        draft.save(update_fields=["estrutura_json"])
        urls = self.rendered("gerador/snippets/urls_app_v2.txt")
        navigation = self.rendered("gerador/snippets/navigation_context.txt")
        self.assertNotIn("relatorios/inativo", urls)
        self.assertNotIn("report_inativo", navigation)
