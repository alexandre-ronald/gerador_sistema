from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class RelatedCollectionComponentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="related-collection", password="x")
        self.sistema = Sistema.objects.create(nome="Central do Fornecedor", usuario=self.user)
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Compras")
        fornecedor = Entidade.objects.create(modulo=modulo, nome="Fornecedor", nome_plural="Fornecedores")
        contrato = Entidade.objects.create(modulo=modulo, nome="Contrato", nome_plural="Contratos")
        Campo.objects.create(entidade=fornecedor, nome="razao_social", tipo="CharField", max_length=120)
        Campo.objects.create(entidade=contrato, nome="numero", tipo="CharField", max_length=40)
        Campo.objects.create(
            entidade=contrato,
            nome="fornecedor",
            tipo="ForeignKey",
            entidade_relacionada=fornecedor,
            related_name_str="contratos",
        )
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "advanced_pages": {
                    "version": 1,
                    "pages": [
                        {
                            "id": "central_fornecedor",
                            "name": "Central do Fornecedor",
                            "slug": "fornecedores/central",
                            "enabled": True,
                            "context": {"kind": "record", "entity": "Fornecedor"},
                            "navigation": {"visible": False, "label": "", "icon": "", "group": "", "order": 0},
                            "components": [
                                {
                                    "id": "contratos",
                                    "type": "table",
                                    "title": "Contratos do fornecedor",
                                    "layout": {"x": 0, "y": 0, "w": 12, "h": 3},
                                    "binding": {"kind": "entity", "ref": "Contrato", "field": ""},
                                    "action": "",
                                    "config": {
                                        "relation": {
                                            "source": "page_context",
                                            "source_field": "pk",
                                            "target_field": "fornecedor",
                                        }
                                    },
                                }
                            ],
                            "actions": [],
                        }
                    ],
                },
                "rbac": {"enabled": False, "roles": [], "entities": {}, "reports": {}},
            },
        )
        self.client.force_login(self.user)

    def test_page_designer_exposes_related_collection_controls(self):
        url = reverse("sistema:page_designer", args=[self.sistema.pk])
        response = self.client.get(url, {"pagina": "central_fornecedor"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tabela relacionada")
        self.assertContains(response, "relationTargetField")
        self.assertContains(response, "Nenhum SQL ou lookup manual é necessário")
        self.assertContains(response, "related_entity")

    def test_preview_marks_related_collection_with_context_filter(self):
        url = reverse("sistema:application_preview", args=[self.sistema.pk])
        response = self.client.get(url, {"pagina": "advanced", "pagina_avancada": "central_fornecedor"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-related-component="contratos"')
        self.assertContains(response, 'data-related-entity="Contrato"')
        self.assertContains(response, 'data-related-field="fornecedor"')
        self.assertContains(response, 'data-context-entity="Fornecedor"')
        self.assertContains(response, "data-related-collection-badge")
