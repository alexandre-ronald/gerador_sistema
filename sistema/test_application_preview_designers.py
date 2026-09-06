from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationPreviewDesignerLinkTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="preview_designers", password="x")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Preview Designers", slug="preview-designers")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Operação")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Pedido", nome_plural="Pedidos", gerar_crud_views=True)
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=30)
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={})
        self.client.force_login(self.user)
        self.url = reverse("sistema:application_preview", args=[self.sistema.pk])

    def test_list_preview_links_to_crud_and_permissions_designers(self):
        response = self.client.get(self.url, {"entidade": self.entidade.pk})
        links = response.context["preview"]["designer_links"]
        self.assertEqual([item["id"] for item in links], ["crud", "permissions"])
        self.assertIn(reverse("sistema:crud_designer", args=[self.sistema.pk]), links[0]["url"])
        self.assertIn(f"entidade={self.entidade.pk}", links[0]["url"])
        self.assertContains(response, 'data-preview-designer="crud"')

    def test_form_preview_links_to_form_designer(self):
        response = self.client.get(self.url, {"entidade": self.entidade.pk, "pagina": "form"})
        links = response.context["preview"]["designer_links"]
        self.assertEqual(links[0]["id"], "form")
        self.assertIn(reverse("sistema:form_designer", args=[self.sistema.pk]), links[0]["url"])
        self.assertIn(f"entidade={self.entidade.pk}", links[0]["url"])

    def test_dashboard_preview_links_to_dashboard_builder(self):
        response = self.client.get(self.url, {"entidade": self.entidade.pk, "pagina": "dashboard"})
        links = response.context["preview"]["designer_links"]
        self.assertEqual(links[0]["id"], "dashboard")
        self.assertEqual(links[0]["url"].split("?")[0], reverse("sistema:dashboard_builder", args=[self.sistema.pk]))

    def test_designer_navigation_does_not_mutate_draft(self):
        draft = self.sistema.versoes.get(numero=0)
        before = draft.estrutura_json
        self.client.get(self.url, {"entidade": self.entidade.pk, "pagina": "form", "dispositivo": "mobile"})
        draft.refresh_from_db()
        self.assertEqual(draft.estrutura_json, before)
