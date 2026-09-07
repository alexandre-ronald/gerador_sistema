from types import SimpleNamespace

from django.template import Template
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .advanced_page_generation import prepare_advanced_pages_generation


class AdvancedRecordEntrypointTests(SimpleTestCase):
    def _entity(self):
        module = SimpleNamespace(app_name="compras")
        field = SimpleNamespace(
            nome="nome",
            codigo_nome="nome",
            verbose_nome="Nome",
            verbose_name="Nome",
            tipo="CharField",
        )
        return SimpleNamespace(
            nome="Fornecedor",
            codigo_nome="fornecedor",
            classe_nome="Fornecedor",
            modulo=module,
            campos_geracao=[field],
            descricao="Fornecedores",
            crud_designer_ready=True,
            crud_title="Fornecedores",
            crud_visible_columns=[SimpleNamespace(codigo_nome="nome", tipo="CharField", label="Nome", sortable=True)],
            crud_search_enabled=False,
            crud_filters=[],
            crud_actions=SimpleNamespace(create=True, view=True, edit=True, delete=True),
        )

    def _config(self):
        return {
            "version": 1,
            "pages": [
                {
                    "id": "central_fornecedor",
                    "name": "Central do Fornecedor",
                    "slug": "fornecedores/central",
                    "enabled": True,
                    "context": {"kind": "record", "entity": "Fornecedor"},
                    "navigation": {"visible": False, "label": "", "icon": "", "group": "", "order": 0},
                    "components": [],
                    "actions": [],
                },
                {
                    "id": "painel_fornecedores",
                    "name": "Painel de Fornecedores",
                    "slug": "fornecedores/painel",
                    "enabled": True,
                    "context": {"kind": "collection", "entity": "Fornecedor"},
                    "navigation": {"visible": True, "label": "Painel", "icon": "", "group": "", "order": 0},
                    "components": [],
                    "actions": [],
                },
            ],
        }

    def test_record_page_is_attached_to_context_entity_only(self):
        entity = self._entity()
        prepare_advanced_pages_generation(self._config(), entities=[entity])

        self.assertEqual(
            entity.advanced_record_pages,
            [{
                "id": "central_fornecedor",
                "name": "Central do Fornecedor",
                "url_name": "advanced_page_central_fornecedor",
            }],
        )

    def test_generated_crud_list_exposes_record_page_for_each_row(self):
        entity = self._entity()
        pages = prepare_advanced_pages_generation(self._config(), entities=[entity])
        source = render_to_string(
            "gerador/snippets/html_list.txt",
            {"entidade": entity, "app_name": "compras", "advanced_pages": pages},
        )
        Template(source)

        self.assertIn("Central do Fornecedor", source)
        self.assertIn("{% url 'advanced_page_central_fornecedor' item.pk %}", source)
        self.assertIn("bi-layout-text-window-reverse", source)

    def test_generated_detail_exposes_named_record_page_button(self):
        entity = self._entity()
        pages = prepare_advanced_pages_generation(self._config(), entities=[entity])
        source = render_to_string(
            "gerador/snippets/html_detail.txt",
            {"entidade": entity, "app_name": "compras", "advanced_pages": pages},
        )
        Template(source)

        self.assertIn("Central do Fornecedor", source)
        self.assertIn("{% url 'advanced_page_central_fornecedor' objeto.pk %}", source)
        self.assertNotIn("Painel de Fornecedores</a>", source)
