from django.contrib.auth import get_user_model
from django.test import TestCase

from .application_blueprint import build_application_inventory
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationBlueprintInventoryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="blueprint", password="test123"
        )
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Gestão de Pedidos",
            descricao="Controle do ciclo de pedidos.",
            tipo_sistema=Sistema.TIPO_WORKFLOW,
        )
        comercial = Modulo.objects.create(sistema=self.sistema, nome="Comercial")
        cadastro = Modulo.objects.create(sistema=self.sistema, nome="Cadastros")
        cliente = Entidade.objects.create(modulo=cadastro, nome="Cliente")
        pedido = Entidade.objects.create(modulo=comercial, nome="Pedido")
        Campo.objects.create(entidade=cliente, nome="nome", tipo="CharField")
        Campo.objects.create(
            entidade=pedido,
            nome="cliente",
            tipo="ForeignKey",
            entidade_relacionada=cliente,
        )
        Campo.objects.create(entidade=pedido, nome="valor", tipo="DecimalField")
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "workflows": {"Pedido": {"states": ["novo", "aprovado"]}},
                "rbac": {"roles": [{"id": "gestor", "label": "Gestor"}]},
                "reports": [{"id": "pedidos"}],
                "notifications": [{"id": "pedido_aprovado"}],
                "integrations": [{"id": "erp"}],
            },
        )

    def test_builds_consolidated_inventory_from_existing_contracts(self):
        blueprint = build_application_inventory(self.sistema)
        self.assertEqual(blueprint["application"]["name"], "Gestão de Pedidos")
        self.assertEqual(
            blueprint["inventory"],
            {
                "modules": 2,
                "entities": 2,
                "fields": 3,
                "relationships": 1,
                "workflows": 1,
                "roles": 1,
                "reports": 1,
                "notifications": 1,
                "integrations": 1,
            },
        )

    def test_inventory_is_deterministic_and_does_not_persist_blueprint(self):
        first = build_application_inventory(self.sistema)
        second = build_application_inventory(self.sistema)
        self.assertEqual(first, second)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertNotIn("blueprint", draft.estrutura_json)
        self.assertEqual(
            [item["name"] for item in first["modules"]],
            ["Cadastros", "Comercial"],
        )

    def test_missing_optional_contracts_remain_zero(self):
        VersaoGeracao.objects.filter(sistema=self.sistema, numero=0).update(
            estrutura_json={}
        )
        inventory = build_application_inventory(self.sistema)["inventory"]
        self.assertEqual(inventory["workflows"], 0)
        self.assertEqual(inventory["roles"], 0)
        self.assertEqual(inventory["reports"], 0)
        self.assertEqual(inventory["notifications"], 0)
        self.assertEqual(inventory["integrations"], 0)
