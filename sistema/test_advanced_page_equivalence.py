from django.contrib.auth import get_user_model
from django.template import Template
from django.template.loader import render_to_string
from django.test import TestCase

from .advanced_page_preview import build_advanced_page_preview
from .application_preview import build_preview_shell
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .services import GeradorService


class AdvancedPageEquivalenceTests(TestCase):
    """Gate transversal: contrato persistido -> Preview -> geração -> runtime.

    A intenção não é duplicar todos os testes unitários das camadas, mas garantir
    que IDs estáveis, contexto, componentes e ações sobrevivem ao pipeline inteiro
    sem criar uma segunda fonte de verdade.
    """

    def setUp(self):
        user = get_user_model().objects.create_user(username="gen0709-equivalence", password="x")
        self.sistema = Sistema.objects.create(nome="Equivalência GEN 0709", usuario=user)
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Contratos")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Contrato", gerar_crud_views=True)
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=80, verbose_name="Número")
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=40, verbose_name="Status")

        self.contract = {
            "version": 1,
            "pages": [{
                "id": "contrato_detail",
                "name": "Detalhe Operacional do Contrato",
                "slug": "contratos/detalhe-operacional",
                "enabled": True,
                "context": {"kind": "record", "entity": "Contrato"},
                "navigation": {"visible": False, "label": "Detalhe", "icon": "bi-file-text", "group": "Contratos", "order": 1},
                "components": [
                    {
                        "id": "status_resumo",
                        "type": "field_summary",
                        "title": "Status",
                        "layout": {"x": 0, "y": 0, "w": 4, "h": 1},
                        "binding": {"kind": "field", "ref": "Contrato", "field": "status"},
                        "action": "",
                        "config": {},
                    },
                    {
                        "id": "aprovar",
                        "type": "workflow_action",
                        "title": "Aprovar",
                        "layout": {"x": 4, "y": 0, "w": 4, "h": 1},
                        "binding": {"kind": "workflow", "ref": "Contrato", "field": ""},
                        "action": "aprovar_contrato",
                        "config": {},
                    },
                ],
                "actions": [{
                    "id": "aprovar_contrato",
                    "kind": "workflow",
                    "label": "Aprovar contrato",
                    "target": {"entity": "Contrato", "transition": "aprovar"},
                }],
            }],
        }
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "advanced_pages": self.contract,
                "workflows": {
                    "Contrato": {
                        "enabled": True,
                        "state_field": "status",
                        "initial_state": "rascunho",
                        "states": [
                            {"id": "rascunho", "label": "Rascunho", "final": False, "order": 0},
                            {"id": "aprovado", "label": "Aprovado", "final": True, "order": 1},
                        ],
                        "transitions": [{
                            "id": "aprovar",
                            "label": "Aprovar",
                            "from": ["rascunho"],
                            "to": "aprovado",
                            "enabled": True,
                            "confirm": True,
                            "confirm_message": "Confirmar aprovação do contrato?",
                            "order": 0,
                        }],
                    }
                },
                "rbac": {"enabled": False, "roles": [], "entities": {}, "reports": {}},
            },
        )

    def test_contract_preview_generation_and_runtime_keep_same_identity_and_behavior(self):
        preview = build_preview_shell(self.sistema)
        build_advanced_page_preview(self.sistema, preview, "contrato_detail")
        preview_page = preview["advanced_page"]

        generation = GeradorService(self.sistema.pk)._prepare_context()["advanced_pages"]
        generated_page = generation["pages"][0]

        self.assertEqual(preview_page["id"], self.contract["pages"][0]["id"])
        self.assertEqual(generated_page["id"], self.contract["pages"][0]["id"])
        self.assertEqual(preview_page["context"], generated_page["context"])
        self.assertEqual(
            [component["id"] for component in preview_page["components_projection"]],
            [component["id"] for component in generated_page["components"]],
        )
        self.assertEqual(
            set(preview_page["actions_projection"]),
            {action["id"] for action in generated_page["actions"]},
        )

        preview_action = preview_page["actions_projection"]["aprovar_contrato"]
        generated_action = next(action for action in generated_page["actions"] if action["id"] == "aprovar_contrato")
        self.assertTrue(preview_action["confirm"])
        self.assertEqual(preview_action["confirm_message"], "Confirmar aprovação do contrato?")
        self.assertEqual(generated_action["kind"], "workflow")
        self.assertEqual(generated_action["target"]["transition"], "aprovar")
        self.assertEqual(generated_action["url_name"], "contratos:contrato_transition")
        self.assertTrue(generated_action["requires_pk"])

        runtime_source = render_to_string("gerador/snippets/advanced_pages_runtime.txt", {"advanced_pages": generation})
        compile(runtime_source, "advanced_pages.py", "exec")
        self.assertIn('"contrato_detail": {', runtime_source)
        self.assertIn('"aprovar_contrato": {', runtime_source)
        self.assertIn('"transition": "aprovar"', runtime_source)
        self.assertIn("_workflow_confirmation", runtime_source)
        self.assertIn("WORKFLOWS", runtime_source)
        self.assertIn("can_transition", runtime_source)

        page_source = render_to_string("gerador/snippets/advanced_page_html.txt", {"page": generated_page})
        Template(page_source)
        self.assertIn("advanced_component_status_resumo_visible", page_source)
        self.assertIn("advanced_component_aprovar_action_url", page_source)
        self.assertIn("advanced_component_aprovar_confirm", page_source)
        self.assertIn("advancedWorkflowConfirm_advanced_component_aprovar", page_source)
