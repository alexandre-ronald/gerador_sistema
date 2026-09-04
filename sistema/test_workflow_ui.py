import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class WorkflowDesignerUITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="owner_workflow", password="test123")
        self.other = user_model.objects.create_user(username="other_workflow", password="test123")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Workflow App", slug="workflow-app")
        self.modulo = Modulo.objects.create(sistema=self.sistema, nome="core")
        self.entidade = Entidade.objects.create(modulo=self.modulo, nome="Pedido")
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=30)
        Campo.objects.create(entidade=self.entidade, nome="descricao", tipo="TextField")
        Campo.objects.create(entidade=self.entidade, nome="valor", tipo="DecimalField", max_digits=10, decimal_places=2)
        self.url = reverse("sistema:workflow_designer", args=[self.sistema.id])
        self.save_url = reverse("sistema:salvar_workflows", args=[self.sistema.id])
        self.client.force_login(self.user)

    def payload(self):
        return {
            "workflows": {
                "Pedido": {
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
                            "confirm": True,
                            "confirm_message": "Confirmar aprovação?",
                            "order": 0,
                        }
                    ],
                }
            }
        }

    def test_designer_renders_friendly_workflow_language(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in [
            "Fluxo do processo",
            "Design · GEN-064",
            "Informações do sistema",
            "Usar fluxo de etapas",
            "Onde guardar a etapa atual",
            "Etapa inicial",
            "Etapas",
            "Mudanças de etapa",
            "Como o processo funciona",
            "Adicionar etapa",
            "Adicionar mudança",
            "Nome da etapa",
            "Nome da ação",
            "Vai para",
            "Pode acontecer quando estiver em",
            "Pedir confirmação",
            "Pergunta de confirmação",
        ]:
            self.assertContains(response, text)
        self.assertNotContains(response, "alert(")

    def test_visual_stage_editor_exposes_order_initial_and_final_controls(self):
        response = self.client.get(self.url)
        for text in [
            "wf-state-number",
            "wf-state-head",
            "wf-state-actions",
            "moveState",
            "setInitialState",
            "Mover para cima",
            "Mover para baixo",
            "Definir como inicial",
            "Começa aqui",
            "Organize a sequência, escolha onde começa e marque quais etapas encerram o processo.",
        ]:
            self.assertContains(response, text)

    def test_designer_keeps_internal_workflow_contract(self):
        response = self.client.get(self.url)
        self.assertContains(response, "state_field")
        self.assertContains(response, "initial_state")
        self.assertContains(response, "transitions")
        self.assertContains(response, "estado_")
        self.assertContains(response, "transicao_")
        self.assertContains(response, "status")

    def test_workspace_lists_workflow_link(self):
        response = self.client.get(reverse("sistema:workspace", args=[self.sistema.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Workflow Designer")
        self.assertContains(response, self.url)

    def test_save_persists_workflow_and_preserves_other_draft_keys(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "forms": {"Pedido": {"sections": []}},
                "cruds": {"Pedido": {"title": "Pedidos"}},
                "business_rules": {"Pedido": {"rules": []}},
            },
        )
        response = self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "sucesso")
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertIn("forms", draft.estrutura_json)
        self.assertIn("cruds", draft.estrutura_json)
        self.assertIn("business_rules", draft.estrutura_json)
        workflow = draft.estrutura_json["workflows"]["Pedido"]
        self.assertEqual(workflow["state_field"], "status")
        self.assertEqual(workflow["transitions"][0]["id"], "aprovar")

    def test_saved_workflow_is_loaded_back_into_designer(self):
        response = self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.url)
        self.assertContains(response, "rascunho")
        self.assertContains(response, "aprovar")
        self.assertContains(response, "Confirmar aprovação?")

    def test_save_rejects_unknown_entity(self):
        payload = self.payload()
        payload["workflows"]["Fantasma"] = payload["workflows"].pop("Pedido")
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "unknown_workflow_entity")

    def test_save_rejects_incompatible_state_field(self):
        payload = self.payload()
        payload["workflows"]["Pedido"]["state_field"] = "valor"
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "incompatible_state_field")

    def test_save_rejects_transition_from_final_state(self):
        payload = self.payload()
        payload["workflows"]["Pedido"]["transitions"][0]["from"] = ["aprovado"]
        payload["workflows"]["Pedido"]["transitions"][0]["to"] = "rascunho"
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "final_state_has_outgoing_transition")

    def test_save_requires_workflows_object(self):
        response = self.client.post(self.save_url, data=json.dumps({"workflows": []}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "invalid_workflows_config")

    def test_other_user_cannot_open_or_save(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(
            self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json").status_code,
            404,
        )
