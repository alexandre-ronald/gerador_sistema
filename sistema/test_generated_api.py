import os
import tempfile

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .services import GeradorService


class GeneratedAPITests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="api_gen", password="x")
        self.sistema = Sistema.objects.create(usuario=user, nome="API Runtime", slug="api-runtime", gerar_api_rest=True, caminho_geracao="/tmp/api-runtime")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="solicitacoes")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Solicitacao", gerar_crud_views=True, gerar_endpoints_api=True)
        Campo.objects.create(entidade=self.entidade, nome="titulo", tipo="CharField", max_length=150)
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=30, blank=True)
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={
            "workflows": {"Solicitacao": {"enabled": True, "state_field": "status", "initial_state": "rascunho", "states": [{"id": "rascunho", "label": "Rascunho", "final": False, "order": 0}], "transitions": []}},
            "api": {"enabled": True, "prefix": "api", "version": "v1", "authentication": "session_basic", "entities": {"Solicitacao": {
                "enabled": True, "endpoint": "solicitacoes",
                "operations": {"list": True, "retrieve": True, "create": True, "update": False, "partial_update": True, "destroy": False},
                "fields": ["id", "titulo", "status"], "read_only_fields": ["id", "status"],
                "search_fields": ["titulo"], "ordering_fields": ["titulo"], "default_ordering": ["titulo"], "page_size": 25,
            }}},
        })

    def test_context_materializes_api_contract_with_generated_field_names(self):
        ctx = GeradorService(self.sistema.id)._prepare_context()
        self.assertTrue(ctx["api"]["enabled"])
        entidade = ctx["modulos"][0].entidades_api[0]
        self.assertEqual(entidade.api_endpoint, "solicitacoes")
        self.assertEqual(entidade.api_fields, ["id", "titulo", "status"])
        self.assertEqual(entidade.api_read_only_fields, ["id", "status"])
        self.assertEqual(entidade.api_search_fields, ["titulo"])
        self.assertTrue(entidade.api_has_workflow)

    def test_templates_generate_serializer_viewset_router_and_root_mount(self):
        ctx = GeradorService(self.sistema.id)._prepare_context()
        modulo = ctx["modulos"][0]
        local = {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidades_crud": modulo.entidades_crud, "entidades_api": modulo.entidades_api, "imports_por_app": {}}
        serializers = render_to_string("gerador/snippets/api_serializers.txt", local)
        views = render_to_string("gerador/snippets/api_views.txt", local)
        router = render_to_string("gerador/snippets/api_urls.txt", local)
        root = render_to_string("gerador/snippets/urls_root_v2.txt", ctx)
        settings = render_to_string("gerador/snippets/settings.txt", ctx)
        self.assertIn("class SolicitacaoSerializer", serializers)
        self.assertIn("read_only_fields = ['id', 'status']", serializers)
        self.assertIn("class SolicitacaoViewSet", views)
        self.assertIn("DjangoForgeModelPermissions", views)
        self.assertIn("'partial_update'", views)
        self.assertIn("run_business_rules", views)
        self.assertIn("apply_initial_state", views)
        self.assertIn("router.register(r'solicitacoes'", router)
        self.assertIn("path('api/v1/'", root)
        self.assertIn("'rest_framework'", settings)

    def test_real_generation_writes_api_artifacts_and_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            self.sistema.caminho_geracao = directory
            self.sistema.save(update_fields=["caminho_geracao"])
            GeradorService(self.sistema.id).gerar_projeto_completo()
            app = os.path.join(directory, "solicitacoes")
            self.assertTrue(os.path.isfile(os.path.join(app, "serializers.py")))
            self.assertTrue(os.path.isfile(os.path.join(app, "api_views.py")))
            self.assertTrue(os.path.isfile(os.path.join(app, "api_urls.py")))
            with open(os.path.join(directory, "requirements.txt"), encoding="utf-8") as handle:
                self.assertIn("djangorestframework>=3.16,<4", handle.read())

    def test_disabled_api_preserves_generation_without_drf_artifacts(self):
        draft = self.sistema.versoes.get(numero=0)
        draft.estrutura_json["api"]["enabled"] = False
        draft.save(update_fields=["estrutura_json"])
        with tempfile.TemporaryDirectory() as directory:
            self.sistema.caminho_geracao = directory
            self.sistema.save(update_fields=["caminho_geracao"])
            GeradorService(self.sistema.id).gerar_projeto_completo()
            app = os.path.join(directory, "solicitacoes")
            self.assertFalse(os.path.exists(os.path.join(app, "serializers.py")))
            self.assertFalse(os.path.exists(os.path.join(app, "api_views.py")))
            self.assertFalse(os.path.exists(os.path.join(app, "api_urls.py")))
            with open(os.path.join(directory, "requirements.txt"), encoding="utf-8") as handle:
                self.assertNotIn("djangorestframework", handle.read())

    def test_disabled_operation_is_not_in_allowed_actions(self):
        ctx = GeradorService(self.sistema.id)._prepare_context()
        modulo = ctx["modulos"][0]
        local = {**ctx, "app_name": modulo.app_name, "entidades": modulo.entidades_geracao, "entidades_crud": modulo.entidades_crud, "entidades_api": modulo.entidades_api, "imports_por_app": {}}
        views = render_to_string("gerador/snippets/api_views.txt", local)
        allowed_line = next(line for line in views.splitlines() if "allowed_actions =" in line)
        self.assertIn("'list'", allowed_line)
        self.assertIn("'create'", allowed_line)
        self.assertIn("'partial_update'", allowed_line)
        self.assertNotIn("'update'", allowed_line)
        self.assertNotIn("'destroy'", allowed_line)
