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
        Campo.objects.create(entidade=self.pedido, nome="status", tipo="CharField", verbose_name="Situação")
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={
            "workflows": {
                "Pedido": {
                    "enabled": True,
                    "state_field": "status",
                    "initial_state": "novo",
                    "states": [
                        {"id": "novo", "label": "Novo", "final": False, "order": 0},
                        {"id": "aprovado", "label": "Aprovado", "final": True, "order": 1},
                    ],
                    "transitions": [
                        {"id": "aprovar", "label": "Aprovar pedido", "from": ["novo"], "to": "aprovado", "enabled": True, "confirm": True, "confirm_message": "Confirmar aprovação?", "order": 0},
                    ],
                }
            },
            "rbac": {
                "enabled": True,
                "roles": [{"id": "gestor", "label": "Gestor", "description": "Responsável pela operação comercial", "group": "Gestores", "order": 0}],
                "entities": {
                    "Pedido": {
                        "roles": {"gestor": ["list", "view", "create", "update"]},
                        "transitions": {"aprovar": ["gestor"]},
                    }
                },
            },
            "forms": {"Pedido": {"title": "Registrar pedido", "fields": [{"name": "valor", "visible": True, "width": 12}]}},
            "cruds": {"Pedido": {"title": "Pedidos em andamento", "columns": [{"field": "valor", "visible": True, "sortable": True}], "search": {"enabled": False, "fields": []}, "filters": [], "actions": {"create": True, "view": True, "edit": False, "delete": False}}},
            "reports": {"Pedido": [{"id": "pedidos", "title": "Pedidos por período", "enabled": True}]},
            "dashboard": {"enabled": True, "title": "Visão gerencial", "widgets": [{"id": "total", "type": "metric", "title": "Total de pedidos", "entity": "Pedido"}]},
            "notifications": [{"id": "pedido_aprovado"}], "integrations": [{"id": "erp"}],
        })

    def test_builds_consolidated_inventory_from_existing_contracts(self):
        blueprint = build_application_inventory(self.sistema)
        self.assertEqual(blueprint["application"]["name"], "Gestão de Pedidos")
        self.assertEqual(blueprint["inventory"], {"modules": 2, "entities": 2, "fields": 4, "relationships": 1, "workflows": 1, "roles": 1, "reports": 1, "notifications": 1, "integrations": 1})

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
        valor = next(item for item in pedido["attributes"] if item["name"] == "valor")
        self.assertEqual(valor["label"], "Valor"); self.assertEqual(valor["type"], "Número decimal"); self.assertTrue(valor["required"])

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

    def test_projects_workflow_as_business_process(self):
        process = build_application_inventory(self.sistema)["processes"][0]
        self.assertEqual(process["information"], "Pedido")
        self.assertEqual(process["initial_state"], "Novo")
        self.assertEqual([state["label"] for state in process["states"]], ["Novo", "Aprovado"])
        self.assertEqual(process["transitions"][0]["label"], "Aprovar pedido")
        self.assertEqual(process["transitions"][0]["from"], ["Novo"])
        self.assertEqual(process["transitions"][0]["to"], "Aprovado")
        self.assertTrue(process["transitions"][0]["confirmation"])

    def test_projects_role_responsibilities_in_business_language(self):
        role = build_application_inventory(self.sistema)["responsibilities"][0]
        self.assertEqual(role["name"], "Gestor")
        self.assertEqual(role["description"], "Responsável pela operação comercial")
        self.assertEqual(role["information"], [{"name": "Pedido", "capabilities": ["Listar", "Consultar", "Cadastrar", "Editar"]}])
        self.assertEqual(role["process_actions"], [{"information": "Pedido", "action": "Aprovar pedido"}])
        self.assertNotIn("change_pedido", str(role))

    def test_projects_coverage_and_points_out_unreviewed_design(self):
        readiness = build_application_inventory(self.sistema)["readiness"]
        coverage = {item["key"]: item for item in readiness["coverage"]}
        self.assertEqual(coverage["information"]["configured"], 2)
        self.assertEqual(coverage["forms"]["configured"], 1)
        self.assertEqual(coverage["listings"]["configured"], 1)
        self.assertEqual(coverage["access"]["configured"], 1)
        self.assertEqual(readiness["status"], "attention")
        self.assertEqual(readiness["blocking"], 0)
        self.assertEqual(readiness["attention"], 3)
        messages = [item["message"] for item in readiness["issues"]]
        self.assertIn("O cadastro ainda não foi revisado no Form Designer.", messages)
        self.assertIn("A consulta ainda não foi revisada no CRUD Designer.", messages)
        self.assertIn("O controle de acesso está ativo, mas esta informação ainda não possui responsabilidades definidas.", messages)

    def test_readiness_becomes_ready_when_core_design_is_covered(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        structure = draft.estrutura_json
        structure["forms"]["Cliente"] = {"title": "Cadastrar cliente"}
        structure["cruds"]["Cliente"] = {"title": "Clientes"}
        structure["rbac"]["entities"]["Cliente"] = {
            "roles": {"gestor": ["list", "view"]},
            "transitions": {},
        }
        draft.estrutura_json = structure
        draft.save(update_fields=["estrutura_json"])

        readiness = build_application_inventory(self.sistema)["readiness"]
        self.assertEqual(readiness["status"], "ready")
        self.assertEqual(readiness["label"], "Pronta para avançar")
        self.assertEqual(readiness["coverage_percent"], 100)
        self.assertEqual(readiness["issues"], [])
