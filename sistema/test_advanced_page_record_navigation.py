from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Entidade, Modulo, Sistema, VersaoGeracao


class AdvancedPageRecordNavigationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="record-navigation", password="x")
        self.sistema = Sistema.objects.create(nome="Gestão de Fornecedores", usuario=self.user)
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Fornecedores")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Fornecedor", nome_plural="Fornecedores", gerar_crud_views=True)
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "advanced_pages": {
                    "version": 1,
                    "pages": [
                        {
                            "id": "central_fornecedores",
                            "name": "Central de Fornecedores",
                            "slug": "central-fornecedores",
                            "enabled": True,
                            "context": {"kind": "collection", "entity": "Fornecedor"},
                            "navigation": {"visible": True, "label": "Central de Fornecedores", "icon": "bi-window", "group": "Páginas", "order": 1},
                            "components": [],
                            "actions": [],
                        },
                        {
                            "id": "detalhes_fornecedor",
                            "name": "Detalhes do Fornecedor",
                            "slug": "detalhes-fornecedor",
                            "enabled": True,
                            "context": {"kind": "record", "entity": "Fornecedor"},
                            "navigation": {"visible": True, "label": "Detalhes do Fornecedor", "icon": "bi-card-list", "group": "Páginas", "order": 2},
                            "components": [],
                            "actions": [],
                        },
                    ],
                },
                "rbac": {"enabled": False, "roles": [], "entities": {}, "reports": {}},
            },
        )

    def test_record_page_keeps_entity_navigation_active_and_is_not_added_to_pages_menu(self):
        self.client.force_login(self.user)
        url = reverse("sistema:application_preview", args=[self.sistema.pk])
        response = self.client.get(url, {"pagina": "advanced", "pagina_avancada": "detalhes_fornecedor"})

        self.assertEqual(response.status_code, 200)
        preview = response.context["preview"]
        self.assertEqual(preview["advanced_page"]["id"], "detalhes_fornecedor")
        self.assertEqual([item["id"] for item in preview["advanced_pages"]], ["central_fornecedores"])

        module_items = [item for module in preview["navigation"]["modules"] for item in module["items"]]
        fornecedor = next(item for item in module_items if item["id"] == self.entidade.pk)
        self.assertTrue(fornecedor["active"])

    def test_designer_explains_and_disables_menu_for_record_pages(self):
        self.client.force_login(self.user)
        url = reverse("sistema:page_designer", args=[self.sistema.pk])
        response = self.client.get(url, {"pagina": "detalhes_fornecedor"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Páginas de registro são acessadas a partir de uma listagem")
        self.assertContains(response, "toggle.disabled = isRecord")
        self.assertContains(response, "page.navigation.visible = false")
