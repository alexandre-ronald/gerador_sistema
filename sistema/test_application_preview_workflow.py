from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .application_preview import build_preview_shell
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationPreviewWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="workflow_preview", password="test123")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Gestão de Pedidos",
            interface_nome="Pedidos 360",
            tipo_menu="lateral",
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Operação")
        self.pedido = Entidade.objects.create(
            modulo=modulo,
            nome="Pedido",
            nome_plural="Pedidos",
            gerar_crud_views=True,
        )
        Campo.objects.create(entidade=self.pedido, nome="numero", tipo="CharField", verbose_name="Número")
        Campo.objects.create(entidade=self.pedido, nome="status", tipo="CharField", verbose_name="Status")
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
                            {
                                "id": "enviar",
                                "label": "Enviar para análise",
                                "from": ["rascunho"],
                                "to": "analise",
                                "enabled": True,
                                "confirm": True,
                                "confirm_message": "Enviar este pedido para análise?",
                                "order": 0,
                            },
                            {
                                "id": "aprovar",
                                "label": "Aprovar",
                                "from": ["analise"],
                                "to": "aprovado",
                                "enabled": True,
                                "confirm": False,
                                "confirm_message": "",
                                "order": 1,
                            },
                            {
                                "id": "oculta",
                                "label": "Ação desativada",
                                "from": ["rascunho"],
                                "to": "aprovado",
                                "enabled": False,
                                "confirm": False,
                                "confirm_message": "",
                                "order": 2,
                            },
                        ],
                    }
                }
            },
        )

    def test_projects_initial_state_and_enabled_actions(self):
        preview = build_preview_shell(
            self.sistema,
            selected_entity_id=self.pedido.pk,
            page_kind="workflow",
        )
        page = preview["workflow_page"]
        self.assertEqual(preview["page_kind"], "workflow")
        self.assertEqual(page["current_state"]["id"], "rascunho")
        self.assertEqual(page["current_state"]["label"], "Rascunho")
        self.assertEqual([item["id"] for item in page["transitions"]], ["enviar"])
        self.assertEqual(page["transitions"][0]["to_label"], "Em análise")
        self.assertTrue(page["transitions"][0]["confirm"])
        self.assertEqual(page["transitions"][0]["confirm_message"], "Enviar este pedido para análise?")

    def test_state_selection_is_transient_and_changes_available_actions(self):
        preview = build_preview_shell(
            self.sistema,
            selected_entity_id=self.pedido.pk,
            page_kind="workflow",
            selected_workflow_state="analise",
        )
        page = preview["workflow_page"]
        self.assertEqual(page["current_state"]["id"], "analise")
        self.assertEqual([item["id"] for item in page["transitions"]], ["aprovar"])
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertNotIn("preview", draft.estrutura_json)
        self.assertNotIn("preview_studio", draft.estrutura_json)
        self.assertEqual(draft.estrutura_json["workflows"]["Pedido"]["initial_state"], "rascunho")

    def test_final_state_has_no_available_actions(self):
        preview = build_preview_shell(
            self.sistema,
            selected_entity_id=self.pedido.pk,
            page_kind="workflow",
            selected_workflow_state="aprovado",
        )
        page = preview["workflow_page"]
        self.assertTrue(page["is_final"])
        self.assertEqual(page["transitions"], [])

    def test_invalid_transient_state_falls_back_to_initial_state(self):
        preview = build_preview_shell(
            self.sistema,
            selected_entity_id=self.pedido.pk,
            page_kind="workflow",
            selected_workflow_state="nao_existe",
        )
        self.assertEqual(preview["workflow_page"]["current_state"]["id"], "rascunho")

    def test_workflow_navigation_lists_only_enabled_workflows(self):
        outro = Entidade.objects.create(
            modulo=self.pedido.modulo,
            nome="Historico",
            nome_plural="Históricos",
            gerar_crud_views=False,
        )
        Campo.objects.create(entidade=outro, nome="status", tipo="CharField", verbose_name="Status")
        preview = build_preview_shell(self.sistema, page_kind="workflow")
        self.assertEqual(len(preview["navigation"]["workflows"]), 1)
        self.assertEqual(preview["navigation"]["workflows"][0]["entity"], "Pedido")

    def test_workflow_view_renders_state_actions_and_gen_069_7_notice(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk]),
            {"entidade": self.pedido.pk, "pagina": "workflow"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-preview-page="workflow"')
        self.assertContains(response, "Rascunho")
        self.assertContains(response, "Enviar para análise")
        self.assertContains(response, "Enviar este pedido para análise?")
        self.assertContains(response, "GEN-069.7")
        self.assertNotContains(response, "Ação desativada")

        next_state = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk]),
            {"entidade": self.pedido.pk, "pagina": "workflow", "estado": "analise"},
        )
        self.assertContains(next_state, "Em análise")
        self.assertContains(next_state, "Aprovar")
