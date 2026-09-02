import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class APIDesignerUITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="api_ui", password="x")
        self.other = get_user_model().objects.create_user(username="api_other", password="x")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="API UI",
            slug="api-ui",
            gerar_api_rest=True,
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="core")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Pedido", gerar_endpoints_api=True)
        Campo.objects.create(entidade=self.entidade, nome="titulo", tipo="CharField", max_length=120)
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=30, blank=True)
        self.draft = VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={
            "forms": {"Pedido": {"title": "Pedido"}},
            "workflows": {"Pedido": {
                "enabled": True,
                "state_field": "status",
                "initial_state": "rascunho",
                "states": [{"id": "rascunho", "label": "Rascunho", "final": False, "order": 0}],
                "transitions": [],
            }},
        })
        self.url = reverse("sistema:api_designer", args=[self.sistema.id])
        self.save_url = reverse("sistema:salvar_api_designer", args=[self.sistema.id])
        self.payload = {
            "api": {
                "enabled": True,
                "prefix": "api",
                "version": "v1",
                "authentication": "session_basic",
                "entities": {
                    "Pedido": {
                        "enabled": True,
                        "endpoint": "pedidos",
                        "operations": {"list": True, "retrieve": True, "create": True, "update": False, "partial_update": False, "destroy": False},
                        "fields": ["id", "titulo", "status"],
                        "read_only_fields": ["id", "status"],
                        "search_fields": ["titulo"],
                        "ordering_fields": ["titulo"],
                        "default_ordering": ["titulo"],
                        "page_size": 25,
                    }
                },
            }
        }

    def test_designer_renders_contract_and_no_alert(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "API Designer")
        self.assertContains(response, "Pedido")
        self.assertContains(response, "Operações REST")
        self.assertContains(response, "Read-only")
        self.assertNotContains(response, "alert(")

    def test_save_persists_api_and_preserves_other_draft_sections(self):
        self.client.force_login(self.user)
        response = self.client.post(self.save_url, data=json.dumps(self.payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.draft.refresh_from_db()
        self.assertIn("forms", self.draft.estrutura_json)
        self.assertIn("workflows", self.draft.estrutura_json)
        api = self.draft.estrutura_json["api"]
        self.assertTrue(api["enabled"])
        self.assertEqual(api["entities"]["Pedido"]["endpoint"], "pedidos")
        self.assertIn("status", api["entities"]["Pedido"]["read_only_fields"])

    def test_saved_config_is_loaded_back(self):
        self.client.force_login(self.user)
        self.client.post(self.save_url, data=json.dumps(self.payload), content_type="application/json")
        response = self.client.get(self.url)
        self.assertContains(response, '"endpoint": "pedidos"')
        self.assertContains(response, '"search_fields": ["titulo"]')

    def test_rejects_entity_without_endpoint_flag(self):
        self.entidade.gerar_endpoints_api = False
        self.entidade.save(update_fields=["gerar_endpoints_api"])
        self.client.force_login(self.user)
        response = self.client.post(self.save_url, data=json.dumps(self.payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "api_entity_not_eligible")

    def test_rejects_api_when_system_flag_is_disabled(self):
        self.sistema.gerar_api_rest = False
        self.sistema.save(update_fields=["gerar_api_rest"])
        self.client.force_login(self.user)
        response = self.client.post(self.save_url, data=json.dumps(self.payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "system_api_disabled")

    def test_rejects_unknown_field(self):
        payload = json.loads(json.dumps(self.payload))
        payload["api"]["entities"]["Pedido"]["fields"].append("fantasma")
        self.client.force_login(self.user)
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "unknown_api_field")

    def test_other_user_cannot_open_or_save(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.save_url, data=json.dumps(self.payload), content_type="application/json").status_code, 404)

    def test_workspace_lists_api_designer(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sistema:lista"))
        self.assertContains(response, "API Designer")
        self.assertContains(response, self.url)
