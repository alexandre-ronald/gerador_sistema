import os
import tempfile

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .services import GeradorService


class GeneratedNotificationCenterTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="notification_runtime", password="x")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sistema = Sistema.objects.create(
            usuario=user,
            nome="Notification Runtime",
            slug="notification-runtime",
            caminho_geracao=self.tmp.name,
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="core")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Contrato", gerar_crud_views=True)
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=30)
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
                            "message": "Um novo contrato foi cadastrado.",
                            "audience": "users_with_view_permission",
                        }
                    ]
                }
            },
        )

    def context(self):
        return GeradorService(self.sistema.id)._prepare_context()

    def test_context_enables_center_when_there_is_an_active_rule(self):
        ctx = self.context()
        self.assertTrue(ctx["notifications"]["enabled"])
        self.assertIn("Contrato", ctx["notifications"]["entities"])

    def test_runtime_contract_is_user_scoped_and_post_only_for_mutations(self):
        views = render_to_string("gerador/snippets/notification_views.txt", self.context())
        self.assertIn("Notification.objects.filter(recipient=request.user)", views)
        self.assertIn("get_object_or_404(Notification, pk=pk, recipient=request.user)", views)
        self.assertIn("@require_POST", views)
        self.assertIn("read_at__isnull=True", views)
        self.assertNotIn("eval(", views)
        self.assertNotIn("exec(", views)

    def test_generated_settings_urls_and_navigation_expose_center(self):
        ctx = self.context()
        settings = render_to_string("gerador/snippets/settings.txt", ctx)
        urls = render_to_string("gerador/snippets/urls_root_v2.txt", ctx)
        navigation = render_to_string("gerador/snippets/navigation_context.txt", ctx)
        self.assertIn("djangoforge_notifications.apps.DjangoForgeNotificationsConfig", settings)
        self.assertIn("path('notifications/', include('djangoforge_notifications.urls'))", urls)
        self.assertIn('"url_name": "notifications:list"', navigation)
        self.assertIn("_notification_unread_count", navigation)
        self.assertIn('item["label"] = f"Notificações ({unread_count})"', navigation)

    def test_real_generation_emits_center_model_migration_and_template(self):
        logs = GeradorService(self.sistema.id).gerar_projeto_completo()
        expected = [
            "djangoforge_notifications/models.py",
            "djangoforge_notifications/views.py",
            "djangoforge_notifications/urls.py",
            "djangoforge_notifications/migrations/0001_initial.py",
            "templates/notifications/list.html",
        ]
        for relative in expected:
            self.assertTrue(os.path.isfile(os.path.join(self.tmp.name, relative)), relative)
        with open(os.path.join(self.tmp.name, "djangoforge_notifications", "models.py"), encoding="utf-8") as handle:
            models_runtime = handle.read()
        self.assertIn("class Notification(models.Model):", models_runtime)
        self.assertIn("read_at = models.DateTimeField", models_runtime)
        self.assertTrue(any("Validação concluída" in item for item in logs))

    def test_gen0664_does_not_dispatch_from_crud_yet(self):
        GeradorService(self.sistema.id).gerar_projeto_completo()
        with open(os.path.join(self.tmp.name, "core", "views.py"), encoding="utf-8") as handle:
            views = handle.read()
        self.assertNotIn("Notification.objects.create", views)
        self.assertNotIn("dispatch_notification", views)
        self.assertNotIn("notify_", views)

    def test_center_is_not_generated_without_active_rules(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        draft.estrutura_json = {
            "notifications": {
                "Contrato": [
                    {
                        "id": "contrato_criado",
                        "enabled": False,
                        "event": "created",
                        "title": "Novo contrato",
                        "message": "Um novo contrato foi cadastrado.",
                        "audience": "users_with_view_permission",
                    }
                ]
            }
        }
        draft.save(update_fields=["estrutura_json"])
        ctx = self.context()
        self.assertFalse(ctx["notifications"]["enabled"])
        settings = render_to_string("gerador/snippets/settings.txt", ctx)
        urls = render_to_string("gerador/snippets/urls_root_v2.txt", ctx)
        self.assertNotIn("djangoforge_notifications", settings)
        self.assertNotIn("djangoforge_notifications.urls", urls)
