import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class PermissionDesignerUITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="owner_rbac", password="test123")
        self.other = user_model.objects.create_user(username="other_rbac", password="test123")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="RBAC App", slug="rbac-app")
        self.modulo = Modulo.objects.create(sistema=self.sistema, nome="core")
        self.entidade = Entidade.objects.create(modulo=self.modulo, nome="Pedido")
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=30)
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
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
                            {"id": "aprovar", "label": "Aprovar", "from": ["rascunho"], "to": "aprovado", "enabled": True, "confirm": False, "confirm_message": "", "order": 0}
                        ],
                    }
                },
                "forms": {"Pedido": {"sections": []}},
            },
        )
        self.url = reverse("sistema:permission_designer", args=[self.sistema.id])
        self.save_url = reverse("sistema:salvar_rbac", args=[self.sistema.id])
        self.client.force_login(self.user)

    def payload(self):
        return {
            "rbac": {
                "enabled": True,
                "roles": [
                    {"id": "operador", "label": "Operador", "group": "Operadores", "order": 0},
                    {"id": "gestor", "label": "Gestor", "group": "Gestores", "order": 1},
                ],
                "entities": {
                    "Pedido": {
                        "roles": {
                            "operador": ["list", "view", "create"],
                            "gestor": ["list", "view", "create", "update", "delete"],
                        },
                        "transitions": {"aprovar": ["gestor"]},
                    }
                },
            }
        }

    def test_designer_renders_roles_crud_and_workflow_matrix(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Permission Designer")
        self.assertContains(response, "Matriz de permissões CRUD")
        self.assertContains(response, "Permissões de Workflow")
        self.assertContains(response, "Pedido")
        self.assertContains(response, "aprovar")
        self.assertNotContains(response, "alert(")

    def test_save_persists_rbac_and_preserves_other_draft_keys(self):
        response = self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertIn("forms", draft.estrutura_json)
        self.assertIn("workflows", draft.estrutura_json)
        self.assertTrue(draft.estrutura_json["rbac"]["enabled"])
        self.assertEqual(draft.estrutura_json["rbac"]["entities"]["Pedido"]["transitions"]["aprovar"], ["gestor"])

    def test_saved_configuration_is_loaded_back(self):
        self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json")
        response = self.client.get(self.url)
        self.assertContains(response, "Operadores")
        self.assertContains(response, "Gestores")
        self.assertContains(response, "operador")

    def test_rejects_unknown_entity(self):
        payload = self.payload()
        payload["rbac"]["entities"]["Fantasma"] = payload["rbac"]["entities"].pop("Pedido")
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "unknown_rbac_entity")

    def test_rejects_unknown_transition(self):
        payload = self.payload()
        payload["rbac"]["entities"]["Pedido"]["transitions"] = {"publicar": ["gestor"]}
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "unknown_transition_reference")

    def test_requires_rbac_object(self):
        response = self.client.post(self.save_url, data=json.dumps({"rbac": []}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "invalid_rbac_config")

    def test_other_user_cannot_open_or_save(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json").status_code, 404)

    def test_workspace_lists_permission_designer_link(self):
        response = self.client.get(reverse("sistema:lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Permission Designer")
        self.assertContains(response, self.url)
