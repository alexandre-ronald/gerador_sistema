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
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=30)
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

    def workflow(self):
        return {
            "enabled": True,
            "state_field": "status",
            "initial_state": "rascunho",
            "states": [
                {"id": "rascunho", "label": "Rascunho", "final": False, "order": 0},
                {"id": "analise", "label": "Em análise", "final": False, "order": 1},
                {"id": "aprovado", "label": "Aprovado", "final": True, "order": 2},
            ],
            "transitions": [
                {
                    "id": "enviar_analise",
                    "label": "Enviar para análise",
                    "from": ["rascunho"],
                    "to": "analise",
                    "enabled": True,
                    "confirm": False,
                    "confirm_message": "",
                    "order": 0,
                },
                {
                    "id": "aprovar",
                    "label": "Aprovar",
                    "from": ["analise"],
                    "to": "aprovado",
                    "enabled": True,
                    "confirm": True,
                    "confirm_message": "Confirmar aprovação?",
                    "order": 1,
                },
            ],
        }

    def rbac(self):
        return {
            "enabled": True,
            "roles": [
                {"id": "operador", "label": "Operador", "group": "Operadores", "order": 0},
                {"id": "gestor", "label": "Gestor", "group": "Gestores", "order": 1},
            ],
            "entities": {},
        }

    def test_designer_renders_friendly_language(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in [
            "Design · GEN-066",
            "Notificações",
            "Nova notificação",
            "Quando avisar",
            "Quem deve receber?",
            "Quem pode visualizar esta informação",
            "Quem realizou a ação",
            "Usuários de um papel",
            "Título da notificação",
            "Mensagem",
            "Salvar notificações",
            "Mudança de situação",
        ]:
            self.assertContains(response, text)
        self.assertNotContains(response, "alert(")

    def test_designer_exposes_enabled_workflow_transitions_as_business_events(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"workflows": {"Contrato": self.workflow()}},
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "enviar_analise")
        self.assertContains(response, "Enviar para análise")
        self.assertContains(response, "Rascunho")
        self.assertContains(response, "Em análise")
        self.assertContains(response, "aprovar")
        self.assertContains(response, "Aprovado")

    def test_designer_exposes_rbac_roles_as_recipient_options(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"rbac": self.rbac()},
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "operador")
        self.assertContains(response, "Operador")
        self.assertContains(response, "gestor")
        self.assertContains(response, "Gestor")

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
        self.assertEqual(rule["audience"], "users_with_view_permission")

    def test_save_persists_actor_recipient(self):
        payload = self.payload()
        payload["notifications"]["Contrato"][0]["audience"] = "actor"
        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        saved = draft.estrutura_json["notifications"]["Contrato"][0]
        self.assertEqual(saved["audience"], "actor")
        self.assertNotIn("role", saved)

    def test_save_persists_rbac_role_recipient(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"rbac": self.rbac()},
        )
        payload = self.payload()
        rule = payload["notifications"]["Contrato"][0]
        rule["audience"] = "role"
        rule["role"] = "gestor"

        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        saved = draft.estrutura_json["notifications"]["Contrato"][0]
        self.assertEqual(saved["audience"], "role")
        self.assertEqual(saved["role"], "gestor")
        self.assertIn("rbac", draft.estrutura_json)

    def test_save_rejects_unknown_role_recipient(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"rbac": self.rbac()},
        )
        payload = self.payload()
        rule = payload["notifications"]["Contrato"][0]
        rule["audience"] = "role"
        rule["role"] = "papel_inexistente"

        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Papel destinatário inválido", response.json()["mensagem"])

    def test_save_rejects_role_recipient_when_rbac_is_disabled(self):
        rbac = self.rbac()
        rbac["enabled"] = False
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"rbac": rbac},
        )
        payload = self.payload()
        rule = payload["notifications"]["Contrato"][0]
        rule["audience"] = "role"
        rule["role"] = "gestor"

        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("RBAC não está ativo", response.json()["mensagem"])

    def test_save_rejects_role_when_audience_is_not_role(self):
        payload = self.payload()
        payload["notifications"]["Contrato"][0]["role"] = "gestor"
        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Papel só pode ser informado", response.json()["mensagem"])

    def test_save_persists_workflow_transition_event(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"workflows": {"Contrato": self.workflow()}},
        )
        payload = self.payload()
        rule = payload["notifications"]["Contrato"][0]
        rule["id"] = "contrato_aprovado"
        rule["event"] = "workflow_transition"
        rule["transition"] = "aprovar"
        rule["title"] = "Contrato aprovado"

        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        saved = draft.estrutura_json["notifications"]["Contrato"][0]
        self.assertEqual(saved["event"], "workflow_transition")
        self.assertEqual(saved["transition"], "aprovar")
        self.assertIn("workflows", draft.estrutura_json)

    def test_save_rejects_unknown_workflow_transition(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"workflows": {"Contrato": self.workflow()}},
        )
        payload = self.payload()
        rule = payload["notifications"]["Contrato"][0]
        rule["event"] = "workflow_transition"
        rule["transition"] = "transicao_inexistente"

        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Transição de workflow inválida", response.json()["mensagem"])

    def test_save_rejects_workflow_event_when_workflow_is_disabled(self):
        workflow = self.workflow()
        workflow["enabled"] = False
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"workflows": {"Contrato": workflow}},
        )
        payload = self.payload()
        rule = payload["notifications"]["Contrato"][0]
        rule["event"] = "workflow_transition"
        rule["transition"] = "aprovar"

        response = self.client.post(
            self.save_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Workflow não está ativo", response.json()["mensagem"])

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
