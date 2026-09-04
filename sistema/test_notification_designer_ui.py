import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class NotificationDesignerUITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="owner_notifications", password="test123")
        self.other = user_model.objects.create_user(username="other_notifications", password="test123")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Notifications App", slug="notifications-app")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="core")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Contrato")
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=30)
        self.url = reverse("sistema:notification_designer", args=[self.sistema.id])
        self.save_url = reverse("sistema:salvar_notifications", args=[self.sistema.id])
        self.client.force_login(self.user)

    def payload(self):
        return {
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
        }

    def test_designer_renders_friendly_language(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in [
            "Design · GEN-066",
            "Notificações",
            "Nova notificação",
            "Quando avisar",
            "Título da notificação",
            "Mensagem",
            "Salvar notificações",
        ]:
            self.assertContains(response, text)
        self.assertNotContains(response, "alert(")

    def test_save_persists_notifications_and_preserves_existing_keys(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"reports": {"Contrato": []}},
        )
        response = self.client.post(
            self.save_url,
            data=json.dumps(self.payload()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertIn("reports", draft.estrutura_json)
        rule = draft.estrutura_json["notifications"]["Contrato"][0]
        self.assertEqual(rule["event"], "created")
        self.assertEqual(rule["title"], "Novo contrato")

    def test_save_rejects_invalid_event(self):
        payload = self.payload()
        payload["notifications"]["Contrato"][0]["event"] = "unknown"
        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Evento de notificação inválido", response.json()["mensagem"])

    def test_other_user_cannot_open_or_save(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(
            self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json").status_code,
            404,
        )
