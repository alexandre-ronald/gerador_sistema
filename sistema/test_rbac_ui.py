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
                    {"id": "operador", "label": "Operador", "description": "Registra e consulta pedidos.", "group": "Operadores", "order": 0},
                    {"id": "gestor", "label": "Gestor", "description": "Aprova e acompanha pedidos.", "group": "Gestores", "order": 1},
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

    def test_designer_uses_business_language_for_roles_and_capabilities(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in [
            "Design · GEN-067",
            "Permission Designer",
            "Controlar acesso por papéis",
            "Papéis do sistema",
            "Nome do papel",
            "O que este papel representa?",
            "O que cada papel pode fazer?",
            "Capacidades sobre as informações",
            "Consultar registros",
            "Ver detalhes",
            "Cadastrar novo",
            "Alterar registros",
            "Excluir registros",
            "Ações do processo",
            "Pedido",
            "Aprovar",
        ]:
            self.assertContains(response, text)
        # GEN-067.2 elimina a matriz CRUD técnica. A seção de Workflow ainda
        # conserva sua própria tabela até a GEN-067.3, portanto não devemos
        # rejeitar genericamente a substring "Informação / Ação".
        for technical_text in ["RBAC ativo", "Django Group", "Matriz de permissões CRUD", "Permissões de Workflow"]:
            self.assertNotContains(response, technical_text)
        self.assertNotContains(response, "<th>Informação / Ação</th>", html=True)
        self.assertNotContains(response, "alert(")

    def test_capabilities_keep_stable_crud_contract(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("list:{label:'Consultar registros'", content)
        self.assertIn("view:{label:'Ver detalhes'", content)
        self.assertIn("create:{label:'Cadastrar novo'", content)
        self.assertIn("update:{label:'Alterar registros'", content)
        self.assertIn("delete:{label:'Excluir registros'", content)
        self.assertIn("toggleCrud", content)

    def test_save_persists_role_description_and_preserves_other_draft_keys(self):
        response = self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertIn("forms", draft.estrutura_json)
        self.assertIn("workflows", draft.estrutura_json)
        self.assertTrue(draft.estrutura_json["rbac"]["enabled"])
        roles = {item["id"]: item for item in draft.estrutura_json["rbac"]["roles"]}
        self.assertEqual(roles["gestor"]["description"], "Aprova e acompanha pedidos.")
        self.assertEqual(roles["gestor"]["group"], "Gestores")
        self.assertEqual(draft.estrutura_json["rbac"]["entities"]["Pedido"]["roles"]["operador"], ["list", "view", "create"])
        self.assertEqual(draft.estrutura_json["rbac"]["entities"]["Pedido"]["transitions"]["aprovar"], ["gestor"])

    def test_save_derives_internal_group_when_designer_does_not_send_it(self):
        payload = self.payload()
        payload["rbac"]["roles"][0].pop("group")
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        saved = response.json()["rbac"]
        operador = next(item for item in saved["roles"] if item["id"] == "operador")
        self.assertEqual(operador["group"], "Operador")
        self.assertEqual(operador["description"], "Registra e consulta pedidos.")

    def test_saved_configuration_is_loaded_back(self):
        self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json")
        response = self.client.get(self.url)
        self.assertContains(response, "Aprova e acompanha pedidos.")
        self.assertContains(response, "Registra e consulta pedidos.")
        self.assertContains(response, "Gestor")
        self.assertContains(response, "Operador")

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
        response = self.client.get(reverse("sistema:workspace", args=[self.sistema.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Permission Designer")
        self.assertContains(response, self.url)
