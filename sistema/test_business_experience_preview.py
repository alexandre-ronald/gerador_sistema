from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sistema.advanced_page_metric_preview import enrich_related_metrics_preview
from sistema.advanced_page_preview import build_advanced_page_preview
from sistema.application_preview import build_preview_shell
from sistema.models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


User = get_user_model()


class BusinessExperiencePreviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="business-preview@example.com", password="secret")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Central do Fornecedor")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Compras")
        fornecedor = Entidade.objects.create(modulo=modulo, nome="Fornecedor", gerar_crud_views=True)
        Campo.objects.create(entidade=fornecedor, nome="nome", tipo="CharField", max_length=120, verbose_name="Nome")
        contrato = Entidade.objects.create(modulo=modulo, nome="Contrato", gerar_crud_views=True)
        Campo.objects.create(entidade=contrato, nome="numero", tipo="CharField", max_length=80, verbose_name="Número")
        Campo.objects.create(entidade=contrato, nome="valor", tipo="DecimalField", max_digits=12, decimal_places=2, verbose_name="Valor")
        Campo.objects.create(entidade=contrato, nome="fornecedor", tipo="ForeignKey", entidade_relacionada=fornecedor, on_delete="PROTECT", verbose_name="Fornecedor")
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "advanced_pages": {
                    "version": 1,
                    "pages": [{
                        "id": "central_fornecedor",
                        "name": "Central do Fornecedor",
                        "slug": "fornecedor/central",
                        "enabled": True,
                        "context": {"kind": "record", "entity": "Fornecedor"},
                        "navigation": {"visible": False, "label": "", "icon": "", "group": "", "order": 0},
                        "components": [
                            {
                                "id": "total_contratos", "type": "metric", "title": "Contratos ativos",
                                "layout": {"x": 0, "y": 0, "w": 4, "h": 1},
                                "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "",
                                "config": {"relation": {"source": "page_context", "source_field": "pk", "target_field": "fornecedor"}, "aggregate": {"operation": "count", "field": ""}},
                            },
                            {
                                "id": "contratos", "type": "table", "title": "Contratos do fornecedor",
                                "layout": {"x": 0, "y": 1, "w": 12, "h": 3},
                                "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "",
                                "config": {"relation": {"source": "page_context", "source_field": "pk", "target_field": "fornecedor"}},
                            },
                            {
                                "id": "novo_contrato_btn", "type": "button", "title": "Novo contrato",
                                "layout": {"x": 0, "y": 4, "w": 3, "h": 1},
                                "binding": {"kind": "none", "ref": "", "field": ""}, "action": "novo_contrato", "config": {},
                            },
                        ],
                        "actions": [{
                            "id": "novo_contrato", "kind": "crud", "label": "Novo contrato",
                            "target": {"entity": "Contrato", "operation": "create"},
                            "transport": {"source": "page_context", "source_field": "pk", "target_field": "fornecedor"},
                        }],
                    }],
                },
                "rbac": {"enabled": False, "roles": [], "entities": {}, "reports": {}},
            },
        )

    def test_projection_combines_relation_metric_and_context_action(self):
        preview = build_preview_shell(self.sistema)
        build_advanced_page_preview(self.sistema, preview, "central_fornecedor")
        enrich_related_metrics_preview(preview)
        page = preview["advanced_page"]
        components = {item["id"]: item for item in page["components_projection"]}
        self.assertEqual(components["total_contratos"]["demo_value"], "7")
        self.assertTrue(components["total_contratos"]["special"]["related_metric"])
        self.assertEqual(components["contratos"]["config"]["relation"]["target_field"], "fornecedor")
        transport = page["actions_projection"]["novo_contrato"]["transport_projection"]
        self.assertTrue(transport["active"])
        self.assertEqual(transport["summary"], "Contrato.fornecedor ← Fornecedor atual")
        self.assertEqual(components["novo_contrato_btn"]["action_projection"]["transport_projection"], transport)

    def test_view_renders_composed_business_experience_markers(self):
        self.client.force_login(self.user)
        url = reverse("sistema:application_preview", args=[self.sistema.pk])
        response = self.client.get(url, {"pagina": "advanced", "pagina_avancada": "central_fornecedor"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sistema/application_preview_advanced.html")
        self.assertContains(response, 'data-related-component="contratos"')
        self.assertContains(response, 'data-related-metric="total_contratos"')
        self.assertContains(response, 'data-context-action="novo_contrato_btn"')
        self.assertContains(response, "Contrato.fornecedor ← Fornecedor atual")
