from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from .interface_designer_views import InterfaceDesignerForm
from .models import Sistema, VersaoGeracao
from .services import GeradorService


class InterfaceNotificationHeaderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="interface_notifications",
            password="test123",
        )
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Gestão de Contratos",
            slug="gestao-de-contratos",
            interface_notificacoes=True,
        )
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "notifications": {
                    "Contrato": [
                        {
                            "id": "contrato_criado",
                            "enabled": True,
                            "event": "created",
                            "title": "Novo contrato",
                            "message": "Um contrato foi criado.",
                            "audience": "actor",
                        }
                    ]
                }
            },
        )

    def test_interface_form_exposes_notification_header_toggle(self):
        form = InterfaceDesignerForm(instance=self.sistema)
        self.assertIn("interface_notificacoes", form.fields)
        self.assertTrue(form.initial.get("interface_notificacoes"))

    def test_interface_designer_renders_toggle_and_visual_bell(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("sistema:interface_designer", args=[self.sistema.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="interface_notificacoes"')
        self.assertContains(response, 'id="previewBell"')
        self.assertContains(response, "Exibir notificações no cabeçalho")

    def test_generated_header_uses_existing_unread_notification_count(self):
        ctx = GeradorService(self.sistema.pk)._prepare_context()
        self.assertTrue(ctx["notifications"]["enabled"])
        base = render_to_string("gerador/snippets/base_html.txt", ctx)
        self.assertIn("app-notification-button", base)
        self.assertIn("app-notification-badge", base)
        self.assertIn("notifications:list", base)
        self.assertIn("notification_unread_count", base)
        self.assertIn("bi bi-bell", base)

    def test_generated_header_hides_bell_when_interface_element_is_disabled(self):
        self.sistema.interface_notificacoes = False
        self.sistema.save(update_fields=["interface_notificacoes"])
        ctx = GeradorService(self.sistema.pk)._prepare_context()
        base = render_to_string("gerador/snippets/base_html.txt", ctx)
        self.assertNotIn("app-notification-button", base)
        self.assertNotIn("app-notification-badge", base)
