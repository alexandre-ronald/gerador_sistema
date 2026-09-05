from django.contrib.auth import get_user_model
from django.test import TestCase

from .application_blueprint import build_application_inventory
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationBlueprintInventoryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="blueprint", password="test123")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Gestão de Pedidos", descricao="Controle do ciclo de pedidos.", tipo_sistema=Sistema.TIPO_WORKFLOW)
        comercial = Modulo.objects.create(sistema=self.sistema, nome="Comercial")
        cadastro = Modulo.objects.create(sistema=self.sistema, nome="Cadastros")
        self.cliente = Entidade.objects.create(modulo=cadastro, nome="Cliente", nome_plural="Clientes")
        self.pedido = Entidade.objects.create(modulo=comercial, nome="Pedido", nome_plural="Pedidos")
        Campo.objects.create(entidade=self.cliente, nome="nome", tipo="CharField", verbose_name="Nome do cliente")
        Campo.objects.create(entidade=self.pedido, nome="cliente", tipo="ForeignKey", entidade_relacionada=self.cliente)
        Campo.objects.create(entidade=self.pedido, nome="valor", tipo="DecimalField", blank=False, null=False)
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={
            "workflows": {"Pedido": {"states": ["novo", "aprovado"]}},
            "rbac": {"roles": [{"id": "gestor", "label": "Gestor"}]},
            "forms": {"Pedido": {"title": "Registrar pedido", "fields": [{"name": "valor", "visible": True, "width": 12}]}},
            "cruds": {"Pedido": {"title": "Pedidos em andamento", "columns": [{"field": "valor", "visible": True, "sortable": True}], "search": {"enabled": False, "fields": []}, "filters": [], "actions": {"create": True, "view": True, "edit": False, "delete": False}}},
            "reports": {"Pedido": [{"id": "pedidos", "title": "Pedidos por período", "enabled": True}]},
            "dashboard": {"enabled": True, "title": "Visão gerencial", "widgets": [{"id": "total", "type": "metric", "title": "Total de pedidos", "entity": "Pedido"}]},
            "notifications": [{"id": "pedido_aprovado"}], "integrations": [{"id": "erp"}],
        })

    def test_builds_consolidated_inventory_from_existing_contracts(self):
        blueprint = build_application_inventory(self.sistema)
        self.assertEqual(blueprint["application"]["name"], "Gestão de Pedidos")
        self.assertEqual(blueprint["inventory"], {"modules": 2, "entities": 2, "fields": 3, "relationships": 1, "workflows": 1, "roles": 1, "reports": 1, "notifications": 1, "integrations": 1})

    def test_inventory_is_deterministic_and_does_not_persist_blueprint(self):
        first = build_application_inventory(self.sistema); second = build_application_inventory(self.sistema)
        self.assertEqual(first, second)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertNotIn("blueprint", draft.estrutura_json)
        self.assertEqual([item["name"] for item in first["modules"]], ["Cadastros", "Comercial"])

    def test_missing_optional_contracts_remain_zero(self):
        VersaoGeracao.objects.filter(sistema=self.sistema, numero=0).update(estrutura_json={})
        inventory = build_application_inventory(self.sistema)["inventory"]
        for key in ["workflows", "roles", "reports", "notifications", "integrations"]: self.assertEqual(inventory[key], 0)

    def test_projects_information_in_business_language(self):
        blueprint = build_application_inventory(self.sistema)
        cliente = next(item for item in blueprint["information"] if item["name"] == "Cliente")
        pedido = next(item for item in blueprint["information"] if item["name"] == "Pedido")
        self.assertEqual(cliente["attributes"][0]["label"], "Nome do cliente"); self.assertEqual(cliente["attributes"][0]["type"], "Texto curto")
        self.assertEqual(pedido["attributes"][0]["label"], "Valor"); self.assertEqual(pedido["attributes"][0]["type"], "Número decimal"); self.assertTrue(pedido["attributes"][0]["required"])

    def test_projects_relationships_without_django_terms(self):
        relation = build_application_inventory(self.sistema)["relationships"][0]
        self.assertEqual(relation["source"], "Pedido"); self.assertEqual(relation["target"], "Cliente"); self.assertEqual(relation["kind"], "pertence a")
        self.assertNotIn("ForeignKey", str(build_application_inventory(self.sistema)["relationships"]))

    def test_projects_form_and_listing_experiences(self):
        pedido = next(item for item in build_application_inventory(self.sistema)["experiences"] if item["entity"] == "Pedido")
        self.assertEqual(pedido["form"]["title"], "Registrar pedido")
        self.assertEqual(pedido["listing"]["title"], "Pedidos em andamento")
        self.assertEqual(pedido["listing"]["actions"], ["Cadastrar", "Consultar"])
        self.assertEqual(pedido["reports"][0]["title"], "Pedidos por período")

    def test_projects_dashboard_in_business_language(self):
        dashboard = build_application_inventory(self.sistema)["dashboard"]
        self.assertEqual(dashboard["title"], "Visão gerencial")
        self.assertEqual(dashboard["widgets"][0]["type"], "Indicador")
        self.assertEqual(dashboard["widgets"][0]["information"], "Pedido")
        self.assertNotIn("metric", str(dashboard))
