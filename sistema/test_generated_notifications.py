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
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=30, blank=True)
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "workflows": {
                    "Contrato": {
                        "enabled": True,
                        "state_field": "status",
                        "initial_state": "rascunho",
                        "states": [
                            {"id": "rascunho", "label": "Rascunho", "final": False, "order": 0},
                            {"id": "aprovado", "label": "Aprovado", "final": True, "order": 1},
                        ],
                        "transitions": [
                            {
                                "id": "aprovar",
                                "label": "Aprovar",
                                "from": ["rascunho"],
                                "to": "aprovado",
                                "enabled": True,
                                "confirm": False,
                                "confirm_message": "",
                                "order": 0,
                            }
                        ],
                    }
                },
                "rbac": {
                    "enabled": True,
                    "roles": [
                        {"id": "gestor", "label": "Gestor", "group": "Gestores", "order": 0}
                    ],
                    "entities": {
                        "Contrato": {
                            "roles": {"gestor": ["list", "view", "create", "update", "delete"]},
                            "transitions": {"aprovar": ["gestor"]},
                        }
                    },
                },
                "notifications": {
                    "Contrato": [
                        {
                            "id": "contrato_criado",
                            "enabled": True,
                            "event": "created",
                            "title": "Novo contrato",
                            "message": "Um novo contrato foi cadastrado.",
                            "audience": "users_with_view_permission",
                        },
                        {
                            "id": "contrato_atualizado",
                            "enabled": True,
                            "event": "updated",
                            "title": "Contrato atualizado",
                            "message": "O contrato foi atualizado.",
                            "audience": "actor",
                            "channels": ["in_app"],
                        },
                        {
                            "id": "contrato_excluido",
                            "enabled": True,
                            "event": "deleted",
                            "title": "Contrato excluído",
                            "message": "O contrato foi excluído.",
                            "audience": "role",
                            "role": "gestor",
                        },
                        {
                            "id": "contrato_aprovado",
                            "enabled": True,
                            "event": "workflow_transition",
                            "transition": "aprovar",
                            "title": "Contrato aprovado",
                            "message": "O contrato foi aprovado.",
                            "audience": "role",
                            "role": "gestor",
                        },
                    ]
                },
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
        self.assertIn("djangoforge_notifications.apps.NotificationActorMiddleware", settings)
        self.assertIn("path('notifications/', include('djangoforge_notifications.urls'))", urls)
        self.assertIn('"url_name": "notifications:list"', navigation)
        self.assertIn("_notification_unread_count", navigation)
        self.assertIn('item["label"] = f"Notificações ({unread_count})"', navigation)

    def test_gen0665_runtime_dispatches_crud_workflow_and_recipient_types(self):
        runtime = render_to_string("gerador/snippets/notification_apps.txt", self.context())
        self.assertIn('"event": "created"', runtime)
        self.assertIn('"event": "updated"', runtime)
        self.assertIn('"event": "deleted"', runtime)
        self.assertIn('"event": "workflow_transition"', runtime)
        self.assertIn('"transition": "aprovar"', runtime)
        self.assertIn('"audience": "actor"', runtime)
        self.assertIn('"audience": "role"', runtime)
        self.assertIn('"audience": "users_with_view_permission"', runtime)
        self.assertIn("NotificationActorMiddleware", runtime)
        self.assertIn("post_save.connect", runtime)
        self.assertIn("post_delete.connect", runtime)
        self.assertIn("WorkflowTransitionHistory", runtime)
        self.assertIn("user_permissions__content_type__app_label", runtime)
        self.assertIn("groups__permissions__content_type__app_label", runtime)
        self.assertIn("RBAC_ENTITIES", runtime)
        self.assertIn("recipient_ids = _recipient_ids", runtime)
        self.assertIn("Notification.objects.bulk_create(pending)", runtime)
        self.assertNotIn("eval(", runtime)
        self.assertNotIn("exec(", runtime)

    def test_gen0671_defaults_legacy_rules_to_in_app_channel(self):
        runtime = render_to_string("gerador/snippets/notification_apps.txt", self.context())
        self.assertIn('"id": "contrato_criado"', runtime)
        self.assertIn('"channels": ["in_app"]', runtime)
        self.assertIn('if "in_app" not in rule.get("channels", ["in_app"]):', runtime)

    def test_notification_rules_are_fail_closed_during_generation(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        structure = dict(draft.estrutura_json)
        structure["notifications"] = {
            "Contrato": [
                {
                    "id": "regra_invalida",
                    "enabled": True,
                    "event": "unknown",
                    "title": "Inválida",
                    "message": "Não deve entrar no runtime.",
                    "audience": "actor",
                },
                {
                    "id": "papel_sem_role",
                    "enabled": True,
                    "event": "created",
                    "title": "Inválida",
                    "message": "Não deve entrar no runtime.",
                    "audience": "role",
                },
                {
                    "id": "canal_desconhecido",
                    "enabled": True,
                    "event": "created",
                    "title": "Inválida",
                    "message": "Não deve entrar no runtime.",
                    "audience": "actor",
                    "channels": ["fax"],
                },
                {
                    "id": "sem_canal",
                    "enabled": True,
                    "event": "created",
                    "title": "Inválida",
                    "message": "Não deve entrar no runtime.",
                    "audience": "actor",
                    "channels": [],
                },
            ]
        }
        draft.estrutura_json = structure
        draft.save(update_fields=["estrutura_json"])
        runtime = render_to_string("gerador/snippets/notification_apps.txt", self.context())
        self.assertNotIn("regra_invalida", runtime)
        self.assertNotIn("papel_sem_role", runtime)
        self.assertNotIn("canal_desconhecido", runtime)
        self.assertNotIn("sem_canal", runtime)

    def test_real_generation_emits_center_model_migration_template_and_dispatch_runtime(self):
        logs = GeradorService(self.sistema.id).gerar_projeto_completo()
        expected = [
            "djangoforge_notifications/apps.py",
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
        with open(os.path.join(self.tmp.name, "djangoforge_notifications", "apps.py"), encoding="utf-8") as handle:
            dispatch_runtime = handle.read()
        with open(os.path.join(self.tmp.name, "core", "views.py"), encoding="utf-8") as handle:
            crud_views = handle.read()
        self.assertIn("class Notification(models.Model):", models_runtime)
        self.assertIn("read_at = models.DateTimeField", models_runtime)
        self.assertIn("dispatch_notifications", dispatch_runtime)
        self.assertIn('"channels": ["in_app"]', dispatch_runtime)
        self.assertIn('if "in_app" not in rule.get("channels", ["in_app"]):', dispatch_runtime)
        self.assertIn("post_save.connect", dispatch_runtime)
        self.assertIn("post_delete.connect", dispatch_runtime)
        self.assertNotIn("Notification.objects.create", crud_views)
        self.assertNotIn("dispatch_notifications", crud_views)
        self.assertTrue(any("Validação concluída" in item for item in logs))

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
        self.assertNotIn("NotificationActorMiddleware", settings)