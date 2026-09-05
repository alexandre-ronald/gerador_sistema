from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .application_preview import build_preview_shell
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationPreviewRoleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="role_preview", password="x")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Gestão de Pedidos",
            slug="gestao-pedidos-role-preview",
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Operação")
        self.entidade = Entidade.objects.create(
            modulo=modulo,
            nome="Pedido",
            nome_plural="Pedidos",
            gerar_crud_views=True,
        )
        self.fornecedor = Entidade.objects.create(
            modulo=modulo,
            nome="Fornecedor",
            nome_plural="Fornecedores",
            gerar_crud_views=True,
        )
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=30)
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=30)
        Campo.objects.create(entidade=self.fornecedor, nome="nome", tipo="CharField", max_length=100)
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
                            {"id": "analise", "label": "Em análise", "final": False, "order": 1},
                            {"id": "aprovado", "label": "Aprovado", "final": True, "order": 2},
                        ],
                        "transitions": [
                            {"id": "enviar", "label": "Enviar", "from": ["rascunho"], "to": "analise", "enabled": True, "confirm": False, "confirm_message": "", "order": 0},
                            {"id": "aprovar", "label": "Aprovar", "from": ["analise"], "to": "aprovado", "enabled": True, "confirm": False, "confirm_message": "", "order": 1},
                        ],
                    }
                },
                "rbac": {
                    "enabled": True,
                    "roles": [
                        {"id": "solicitante", "label": "Solicitante", "description": "Abre e acompanha pedidos", "group": "Solicitantes", "order": 0},
                        {"id": "gestor", "label": "Gestor", "description": "Analisa e aprova pedidos", "group": "Gestores", "order": 1},
                        {"id": "operador", "label": "Operador", "description": "Opera pedidos sem acesso a fornecedores", "group": "Operadores", "order": 2},
                    ],
                    "entities": {
                        "Pedido": {
                            "roles": {
                                "solicitante": ["list", "view", "create"],
                                "gestor": ["list", "view", "update"],
                                "operador": ["list", "view", "update"],
                            },
                            "transitions": {
                                "enviar": ["solicitante"],
                                "aprovar": ["gestor"],
                            },
                        },
                        "Fornecedor": {
                            "roles": {
                                "solicitante": ["list", "view"],
                                "gestor": ["list", "view", "create", "update", "delete"],
                                "operador": [],
                            },
                            "transitions": {},
                        },
                    },
                },
            },
        )

    def test_without_role_keeps_complete_design_view(self):
        preview = build_preview_shell(self.sistema, selected_entity_id=self.entidade.pk)
        self.assertFalse(preview["role_simulation"]["active"])
        self.assertEqual(preview["role_simulation"]["mode_label"], "Visão completa de design")
        self.assertTrue(preview["list_page"]["actions"]["create"])
        self.assertTrue(preview["list_page"]["actions"]["edit"])

    def test_selected_role_filters_crud_capabilities(self):
        preview = build_preview_shell(
            self.sistema,
            selected_entity_id=self.entidade.pk,
            selected_role_id="solicitante",
        )
        self.assertTrue(preview["role_simulation"]["active"])
        self.assertEqual(preview["role_simulation"]["selected_role"]["label"], "Solicitante")
        permissions = preview["selected_role_permissions"]
        self.assertTrue(permissions["list"])
        self.assertTrue(permissions["view"])
        self.assertTrue(permissions["create"])
        self.assertFalse(permissions["update"])
        self.assertFalse(permissions["delete"])
        self.assertTrue(preview["list_page"]["actions"]["create"])
        self.assertFalse(preview["list_page"]["actions"]["edit"])
        self.assertFalse(preview["list_page"]["actions"]["delete"])

        manager = build_preview_shell(
            self.sistema,
            selected_entity_id=self.entidade.pk,
            selected_role_id="gestor",
        )
        self.assertTrue(manager["selected_role_permissions"]["update"])
        self.assertTrue(manager["list_page"]["actions"]["edit"])
        self.assertFalse(manager["list_page"]["actions"]["create"])

    def test_selected_role_filters_sidebar_entities_without_list_access(self):
        preview = build_preview_shell(
            self.sistema,
            selected_entity_id=self.fornecedor.pk,
            selected_role_id="operador",
        )
        visible_names = [
            item["name"]
            for module in preview["navigation"]["modules"]
            for item in module["items"]
        ]
        self.assertIn("Pedido", visible_names)
        self.assertNotIn("Fornecedor", visible_names)
        self.assertEqual(preview["list_page"]["entity"], "Pedido")
        self.assertEqual(preview["role_simulation"]["selected_role_id"], "operador")

    def test_selected_role_filters_workflow_by_stable_transition_id(self):
        requester = build_preview_shell(
            self.sistema,
            selected_entity_id=self.entidade.pk,
            page_kind="workflow",
            selected_role_id="solicitante",
        )
        self.assertEqual([item["id"] for item in requester["workflow_page"]["transitions"]], ["enviar"])

        manager_draft = build_preview_shell(
            self.sistema,
            selected_entity_id=self.entidade.pk,
            page_kind="workflow",
            selected_role_id="gestor",
        )
        self.assertEqual(manager_draft["workflow_page"]["transitions"], [])

        manager_analysis = build_preview_shell(
            self.sistema,
            selected_entity_id=self.entidade.pk,
            page_kind="workflow",
            selected_workflow_state="analise",
            selected_role_id="gestor",
        )
        self.assertEqual([item["id"] for item in manager_analysis["workflow_page"]["transitions"]], ["aprovar"])

    def test_role_simulation_is_transient_and_does_not_create_user_membership(self):
        before_groups = list(self.user.groups.values_list("name", flat=True))
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        before = draft.estrutura_json
        build_preview_shell(self.sistema, selected_role_id="gestor")
        draft.refresh_from_db()
        self.assertEqual(before_groups, list(self.user.groups.values_list("name", flat=True)))
        self.assertEqual(draft.estrutura_json, before)
        self.assertNotIn("preview", draft.estrutura_json)
        self.assertNotIn("preview_studio", draft.estrutura_json)

    def test_unknown_role_is_fail_closed_and_not_invented(self):
        preview = build_preview_shell(
            self.sistema,
            selected_entity_id=self.entidade.pk,
            selected_role_id="super_admin_inventado",
        )
        simulation = preview["role_simulation"]
        permissions = preview["selected_role_permissions"]
        self.assertTrue(simulation["invalid_role"])
        self.assertFalse(simulation["active"])
        self.assertIsNone(simulation["selected_role"])
        self.assertEqual(simulation["selected_role_id"], "")
        self.assertEqual(simulation["requested_role_id"], "super_admin_inventado")
        self.assertEqual(simulation["mode_label"], "Papel inválido")
        self.assertTrue(permissions["filtered"])
        self.assertFalse(permissions["list"])
        self.assertFalse(permissions["view"])
        self.assertFalse(permissions["create"])
        self.assertFalse(permissions["update"])
        self.assertFalse(permissions["delete"])
        self.assertEqual(permissions["transitions"], {})
        self.assertFalse(preview["list_page"]["role_access"])
        self.assertFalse(preview["list_page"]["actions"]["create"])
        self.assertFalse(preview["list_page"]["actions"]["view"])
        self.assertFalse(preview["list_page"]["actions"]["edit"])
        self.assertFalse(preview["list_page"]["actions"]["delete"])

        workflow = build_preview_shell(
            self.sistema,
            selected_entity_id=self.entidade.pk,
            page_kind="workflow",
            selected_role_id="super_admin_inventado",
        )
        self.assertEqual(workflow["workflow_page"]["transitions"], [])

    def test_workflow_page_renders_business_role_selector(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk]),
            {"pagina": "workflow", "entidade": self.entidade.pk, "papel": "solicitante"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visualizar como papel")
        self.assertContains(response, "Solicitante")
        self.assertContains(response, 'data-preview-role="solicitante"')
        self.assertContains(response, 'data-transition-id="enviar"')
        self.assertNotContains(response, 'data-transition-id="aprovar"')
        self.assertContains(response, "Nenhuma associação usuário → papel é criada")
