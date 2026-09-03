import json

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class CrudDesignerUITests(SimpleTestCase):
    def source(self):
        return render_to_string("sistema/crud_designer.html", {
            "sistema": type("SistemaStub", (), {"id": 1})(),
            "entities": [],
            "cruds_json": "{}",
            "entity_metadata_json": "{}",
        })

    def test_exposes_crud_designer_shell(self):
        source = self.source()
        self.assertIn("CRUD Designer 2.0", source)
        self.assertIn("Design · GEN-051", source)
        self.assertIn("Voltar ao Workspace", source)
        self.assertIn('id="entity"', source)
        self.assertIn('id="crud-title"', source)
        self.assertIn('id="page-size"', source)
        self.assertIn('id="preview-shell"', source)

    def test_exposes_columns_search_filters_ordering_and_actions(self):
        source = self.source()
        self.assertIn('id="columns"', source)
        self.assertIn('id="search-config"', source)
        self.assertIn('id="filters"', source)
        self.assertIn('id="add-filter"', source)
        self.assertIn('id="actions"', source)
        self.assertIn('id="default-order"', source)
        self.assertIn("data-column-visible", source)
        self.assertIn("data-column-sortable", source)

    def test_preview_is_local_only(self):
        source = self.source()
        self.assertIn("Preview Mode", source)
        self.assertIn("previewMode=true", source)
        self.assertIn("previewMode=false", source)
        self.assertNotIn("preview_mode", source)

    def test_save_uses_cruds_contract_and_professional_notification(self):
        source = self.source()
        self.assertIn("JSON.stringify({cruds})", source)
        self.assertIn("cruds=data.cruds", source)
        self.assertIn("/sistemas/1/crud-designer/salvar/", source)
        self.assertIn("forge-notify", source)
        self.assertNotIn("alert(", source)


class CrudDesignerEndpointTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="crud-owner", password="senha-forte")
        self.other = User.objects.create_user(username="crud-other", password="senha-forte")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="CRUD Teste")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="cadastro")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Pedido")
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", verbose_name="Número", max_length=30)
        Campo.objects.create(entidade=self.entidade, nome="descricao", tipo="TextField", verbose_name="Descrição")
        Campo.objects.create(entidade=self.entidade, nome="ativo", tipo="BooleanField", verbose_name="Ativo")
        self.client.force_login(self.user)

    def test_designer_renders_for_owner(self):
        response = self.client.get(reverse("sistema:crud_designer", args=[self.sistema.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CRUD Designer 2.0")
        self.assertContains(response, '"Pedido"')

    def test_designer_is_not_available_to_other_user(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("sistema:crud_designer", args=[self.sistema.id]))
        self.assertEqual(response.status_code, 404)

    def test_save_persists_normalized_contract_without_destroying_other_draft_data(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho existente",
            estrutura_json={"forms": {"Pedido": {"title": "Form preservado"}}},
        )
        payload = {
            "cruds": {
                "Pedido": {
                    "title": "Pedidos ativos",
                    "page_size": 50,
                    "default_order": "-numero",
                    "columns": [
                        {"field": "numero", "label": "Nº", "order": 0, "visible": True, "sortable": True},
                        {"field": "descricao", "label": "Descrição", "order": 1, "visible": True, "sortable": True},
                    ],
                    "search": {"enabled": True, "fields": ["numero", "descricao"], "placeholder": "Pesquisar pedido"},
                    "filters": [{"field": "ativo", "label": "Situação", "type": "boolean", "order": 0}],
                    "actions": {"create": True, "view": True, "edit": True, "delete": False},
                }
            }
        }
        response = self.client.post(
            reverse("sistema:salvar_crud_designer", args=[self.sistema.id]),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sucesso")
        self.assertEqual(data["cruds"]["Pedido"]["page_size"], 50)
        self.assertFalse(data["cruds"]["Pedido"]["actions"]["delete"])
        versao = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertIn("forms", versao.estrutura_json)
        self.assertIn("cruds", versao.estrutura_json)
        self.assertEqual(versao.estrutura_json["forms"]["Pedido"]["title"], "Form preservado")

    def test_save_rejects_unknown_entity(self):
        response = self.client.post(
            reverse("sistema:salvar_crud_designer", args=[self.sistema.id]),
            data=json.dumps({"cruds": {"Inexistente": {}}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "unknown_entity")

    def test_save_rejects_unsafe_lookup(self):
        payload = {
            "cruds": {
                "Pedido": {
                    "columns": [{"field": "numero__icontains", "visible": True, "sortable": True}],
                    "search": {"enabled": False, "fields": []},
                }
            }
        }
        response = self.client.post(
            reverse("sistema:salvar_crud_designer", args=[self.sistema.id]),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "invalid_column_field")
