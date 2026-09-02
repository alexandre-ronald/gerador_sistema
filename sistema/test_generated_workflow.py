import os
import tempfile

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .services import GeradorService


class GeneratedWorkflowTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="workflow_generator", password="x")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sistema = Sistema.objects.create(usuario=user, nome="Workflow Runtime", slug="workflow-runtime", caminho_geracao=self.tmp.name)
        modulo = Modulo.objects.create(sistema=self.sistema, nome="core")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Pedido", gerar_crud_views=True)
        Campo.objects.create(entidade=self.entidade, nome="descricao", tipo="CharField", max_length=120)
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=30, blank=True)
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={
            "cruds": {"Pedido": {
                "title": "Pedidos", "page_size": 25, "default_order": "",
                "columns": [{"field": "descricao", "label": "Descrição", "order": 0, "visible": True, "sortable": True}, {"field": "status", "label": "Status", "order": 1, "visible": True, "sortable": True}],
                "search": {"enabled": True, "fields": ["descricao"], "placeholder": "Pesquisar"},
                "filters": [], "actions": {"create": True, "view": True, "edit": True, "delete": True},
            }},
            "workflows": {"Pedido": {
                "enabled": True, "state_field": "status", "initial_state": "rascunho",
                "states": [
                    {"id": "rascunho", "label": "Rascunho", "final": False, "order": 0},
                    {"id": "aprovado", "label": "Aprovado", "final": True, "order": 1},
                ],
                "transitions": [{"id": "aprovar", "label": "Aprovar", "from": ["rascunho"], "to": "aprovado", "enabled": True, "confirm": True, "confirm_message": "Confirmar aprovação?", "order": 0}],
            }},
        })

    def rendered(self, template):
        service = GeradorService(self.sistema.id)
        ctx = service._prepare_context()
        modulo = ctx["modulos"][0]
        return render_to_string(template, {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidades_crud": modulo.entidades_crud})

    def test_runtime_is_closed_and_contains_transition_contract(self):
        runtime = self.rendered("gerador/snippets/workflow_runtime.txt")
        self.assertIn('"state_field": "status"', runtime)
        self.assertIn('"initial_state": "rascunho"', runtime)
        self.assertIn('"id": "aprovar"', runtime)
        self.assertIn("def available_transitions(instance):", runtime)
        self.assertIn("def perform_transition(instance, transition_id", runtime)
        self.assertNotIn("eval(", runtime)
        self.assertNotIn("exec(", runtime)

    def test_form_excludes_workflow_state_field(self):
        forms = self.rendered("gerador/snippets/forms_v2.txt")
        self.assertIn('"descricao"', forms)
        self.assertNotIn('            "status",', forms)

    def test_views_apply_initial_state_and_expose_transition_endpoint(self):
        views = self.rendered("gerador/snippets/views.txt")
        urls = self.rendered("gerador/snippets/urls_app_v2.txt")
        self.assertIn("apply_initial_state(form.instance)", views)
        self.assertIn("available_transitions(self.object)", views)
        self.assertIn("perform_transition(objeto, transition_id", views)
        self.assertIn("workflow/<str:transition_id>/", urls)

    def test_real_generation_creates_workflow_runtime_and_history_model(self):
        logs = GeradorService(self.sistema.id).gerar_projeto_completo()
        workflow_path = os.path.join(self.tmp.name, "core", "workflow.py")
        models_path = os.path.join(self.tmp.name, "core", "models.py")
        detail_path = os.path.join(self.tmp.name, "core", "templates", "core", "pedido_detail.html")
        self.assertTrue(os.path.isfile(workflow_path))
        self.assertTrue(os.path.isfile(detail_path))
        with open(workflow_path, encoding="utf-8") as f:
            workflow = f.read()
        with open(models_path, encoding="utf-8") as f:
            models = f.read()
        self.assertIn("aprovar", workflow)
        self.assertIn("class WorkflowTransitionHistory", models)
        self.assertTrue(any("Validação concluída" in item for item in logs))

    def test_no_workflow_keeps_form_state_field_and_no_transition_route(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        draft.estrutura_json = {"cruds": draft.estrutura_json["cruds"]}
        draft.save(update_fields=["estrutura_json"])
        forms = self.rendered("gerador/snippets/forms_v2.txt")
        urls = self.rendered("gerador/snippets/urls_app_v2.txt")
        self.assertIn('            "status",', forms)
        self.assertNotIn("workflow/<str:transition_id>/", urls)
