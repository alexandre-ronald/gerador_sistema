import os
import tempfile

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .services import GeradorService


class GeneratedRBACTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="rbac_generator", password="x")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sistema = Sistema.objects.create(usuario=user, nome="RBAC Runtime", slug="rbac-runtime", caminho_geracao=self.tmp.name)
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
                "states": [{"id": "rascunho", "label": "Rascunho", "final": False, "order": 0}, {"id": "aprovado", "label": "Aprovado", "final": True, "order": 1}],
                "transitions": [{"id": "aprovar", "label": "Aprovar", "from": ["rascunho"], "to": "aprovado", "enabled": True, "confirm": False, "confirm_message": "", "order": 0}],
            }},
            "rbac": {
                "enabled": True,
                "roles": [
                    {"id": "operador", "label": "Operador", "group": "Operadores", "order": 0},
                    {"id": "gestor", "label": "Gestor", "group": "Gestores", "order": 1},
                ],
                "entities": {"Pedido": {
                    "roles": {"operador": ["list", "view", "create"], "gestor": ["list", "view", "create", "update", "delete"]},
                    "transitions": {"aprovar": ["gestor"]},
                }},
            },
        })

    def rendered(self, template):
        service = GeradorService(self.sistema.id)
        ctx = service._prepare_context()
        modulo = ctx["modulos"][0]
        return render_to_string(template, {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidades_crud": modulo.entidades_crud})

    def test_runtime_contains_closed_role_and_transition_contract(self):
        runtime = self.rendered("gerador/snippets/rbac_runtime.txt")
        self.assertIn('"operador": {"label": "Operador", "group": "Operadores"}', runtime)
        self.assertIn('"gestor": {"label": "Gestor", "group": "Gestores"}', runtime)
        self.assertIn('"aprovar": ["gestor"]', runtime)
        self.assertIn("def require_entity_action(user, entity_name, action):", runtime)
        self.assertIn("def require_transition(user, entity_name, transition_id):", runtime)
        self.assertIn("def filter_transitions(user, entity_name, transitions):", runtime)
        self.assertNotIn("eval(", runtime)
        self.assertNotIn("exec(", runtime)

    def test_views_enforce_rbac_and_filter_workflow_actions(self):
        views = self.rendered("gerador/snippets/views.txt")
        self.assertIn("require_entity_action(request.user, 'Pedido', 'list')", views)
        self.assertIn("require_entity_action(request.user, 'Pedido', 'create')", views)
        self.assertIn("require_entity_action(request.user, 'Pedido', 'update')", views)
        self.assertIn("require_entity_action(request.user, 'Pedido', 'delete')", views)
        self.assertIn("filter_transitions(self.request.user, 'Pedido', transitions)", views)
        self.assertIn("require_transition(request.user, 'Pedido', transition_id)", views)
        self.assertIn("raise PermissionDenied(str(exc))", views)

    def test_real_generation_emits_rbac_runtime(self):
        logs = GeradorService(self.sistema.id).gerar_projeto_completo()
        path = os.path.join(self.tmp.name, "core", "rbac.py")
        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8") as handle:
            runtime = handle.read()
        self.assertIn("RBAC_ENABLED = True", runtime)
        self.assertIn("Operadores", runtime)
        self.assertIn("Gestores", runtime)
        self.assertTrue(any("Validação concluída" in item for item in logs))

    def test_no_rbac_keeps_gen053_view_behavior(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        structure = dict(draft.estrutura_json)
        structure.pop("rbac")
        draft.estrutura_json = structure
        draft.save(update_fields=["estrutura_json"])
        views = self.rendered("gerador/snippets/views.txt")
        self.assertNotIn("from .rbac import", views)
        self.assertNotIn("require_entity_action(request.user", views)
        self.assertNotIn("require_transition(request.user", views)
        self.assertIn("perform_transition(objeto, transition_id", views)
