from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class GeneratedAdvancedPagesRuntimeTests(SimpleTestCase):
    def pages(self):
        return {"pages": [
            {
                "id": "inicio_operacional", "name": "Início Operacional", "slug": "operacao", "url_name": "advanced_page_inicio_operacional", "requires_pk": False,
                "context": {"kind": "none", "entity": ""}, "context_app_name": "", "context_model_name": "", "components": [],
            },
            {
                "id": "contratos", "name": "Contratos", "slug": "central/contratos", "url_name": "advanced_page_contratos", "requires_pk": False,
                "context": {"kind": "collection", "entity": "Contrato"}, "context_app_name": "contratos", "context_model_name": "Contrato", "components": [],
            },
            {
                "id": "contrato_detail", "name": "Contrato", "slug": "contratos/detalhe", "url_name": "advanced_page_contrato_detail", "requires_pk": True,
                "context": {"kind": "record", "entity": "Contrato"}, "context_app_name": "contratos", "context_model_name": "Contrato", "components": [],
            },
        ]}

    def test_generated_runtime_supports_none_collection_and_record(self):
        source = render_to_string("gerador/snippets/advanced_pages_runtime.txt", {"advanced_pages": self.pages()})
        compile(source, "advanced_pages.py", "exec")
        self.assertIn('"context_kind": "none"', source)
        self.assertIn('"context_kind": "collection"', source)
        self.assertIn('"context_kind": "record"', source)
        self.assertIn('has_entity_action(request.user, entity_name, action)', source)
        self.assertIn('get_object_or_404(_model_for(page), pk=pk)', source)
        self.assertIn('_default_manager.all()', source)

    def test_generated_root_urls_emit_record_and_collection_routes(self):
        source = render_to_string("gerador/snippets/urls_root_v2.txt", {
            "sistema": SimpleNamespace(nome="Teste"),
            "runtime_rbac": {"enabled": False, "roles": []},
            "advanced_pages": self.pages(),
            "notifications": {"enabled": False},
            "api": {"enabled": False},
            "modulos": [],
        })
        compile(source, "urls.py", "exec")
        self.assertIn("path('central/contratos/', advanced_page_view", source)
        self.assertIn("path('contratos/detalhe/<int:pk>/', advanced_page_view", source)
        self.assertIn("name='advanced_page_contrato_detail'", source)
