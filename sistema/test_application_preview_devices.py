from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationPreviewDeviceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="device_preview", password="x")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Preview Responsivo", slug="preview-responsivo")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Operação")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Pedido", nome_plural="Pedidos", gerar_crud_views=True)
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=30)
        self.draft = VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={})
        self.client.force_login(self.user)
        self.url = reverse("sistema:application_preview", args=[self.sistema.pk])

    def test_default_device_is_desktop(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["preview"]["device_preview"]["selected"], "desktop")
        self.assertContains(response, 'data-preview-device="desktop"')
        self.assertContains(response, 'data-preview-device-container="desktop"')

    def test_tablet_and_mobile_are_transient(self):
        before = self.draft.estrutura_json
        for device in ("tablet", "mobile"):
            response = self.client.get(self.url, {"entidade": self.entidade.pk, "dispositivo": device})
            self.assertEqual(response.context["preview"]["device_preview"]["selected"], device)
            self.assertContains(response, f'data-preview-device-container="{device}"')
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.estrutura_json, before)
        self.assertNotIn("device", self.draft.estrutura_json)
        self.assertNotIn("dispositivo", self.draft.estrutura_json)

    def test_invalid_device_normalizes_to_desktop(self):
        response = self.client.get(self.url, {"dispositivo": "televisao"})
        device = response.context["preview"]["device_preview"]
        self.assertEqual(device["selected"], "desktop")
        self.assertTrue(device["invalid"])
        self.assertContains(response, "Dispositivo desconhecido normalizado para Desktop")

    def test_role_form_preserves_selected_device(self):
        response = self.client.get(self.url, {"entidade": self.entidade.pk, "dispositivo": "mobile"})
        self.assertContains(response, 'name="dispositivo" value="mobile"', html=True)

    def test_device_links_preserve_page_context(self):
        response = self.client.get(
            self.url,
            {"entidade": self.entidade.pk, "pagina": "form", "dispositivo": "tablet"},
        )
        self.assertContains(response, f"entidade={self.entidade.pk}")
        self.assertContains(response, "pagina=form")
        self.assertContains(response, "dispositivo=mobile")
