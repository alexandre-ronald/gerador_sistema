from types import SimpleNamespace

from django.template import Template
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .advanced_page_generation import prepare_advanced_pages_generation


class GeneratedAdvancedPageTemplateTests(SimpleTestCase):
    def entity(self):
        module = SimpleNamespace(app_name="contratos")
        fields = [
            SimpleNamespace(nome="numero", codigo_nome="numero", verbose_nome="Número", verbose_name="Número", tipo="CharField"),
            SimpleNamespace(nome="status", codigo_nome="status", verbose_nome="Status", verbose_name="Status", tipo="CharField"),
        ]
        return SimpleNamespace(nome="Contrato", codigo_nome="contrato", classe_nome="Contrato", modulo=module, campos_geracao=fields)

    def config(self):
        return {
            "version": 1,
            "pages": [{
                "id": "contrato_detail",
                "name": "Detalhe do Contrato",
                "slug": "contratos/detalhe",
                "enabled": True,
                "context": {"kind": "record", "entity": "Contrato"},
                "navigation": {"visible": True, "label": "Detalhe", "icon": "", "group": "Contratos", "order": 0},
                "components": [
                    {"id": "titulo", "type": "title", "title": "Contrato", "layout": {"x": 0, "y": 0, "w": 12, "h": 1}, "binding": {"kind": "none", "ref": "", "field": ""}, "action": "", "config": {}},
                    {"id": "status", "type": "field_summary", "title": "Status", "layout": {"x": 0, "y": 1, "w": 4, "h": 1}, "binding": {"kind": "field", "ref": "Contrato", "field": "status"}, "action": "", "config": {}},
                    {"id": "detalhe", "type": "record_detail", "title": "Dados", "layout": {"x": 0, "y": 2, "w": 12, "h": 2}, "binding": {"kind": "page_context", "ref": "", "field": ""}, "action": "", "config": {}},
                    {"id": "tabela", "type": "table", "title": "Contratos", "layout": {"x": 0, "y": 4, "w": 12, "h": 3}, "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "", "config": {}},
                ],
                "actions": [],
            }],
        }

    def page(self):
        return prepare_advanced_pages_generation(self.config(), entities=[self.entity()])["pages"][0]

    def test_generation_adds_field_and_runtime_metadata(self):
        page = self.page()
        status = page["components"][1]
        detail = page["components"][2]
        self.assertEqual(status["runtime_key"], "advanced_component_status")
        self.assertEqual(status["binding_field"]["code"], "status")
        self.assertEqual([field["code"] for field in detail["binding_fields"]], ["numero", "status"])

    def test_generated_page_template_is_valid_django_template(self):
        source = render_to_string("gerador/snippets/advanced_page_html.txt", {"page": self.page()})
        Template(source)
        self.assertIn("advanced_component_status_visible", source)
        self.assertIn("{{ advanced_component_status }}", source)
        self.assertIn("{% for row in advanced_component_tabela %}", source)
        self.assertIn("{{ row.numero }}", source)
        self.assertIn("grid-template-columns:repeat(12", source)

    def test_runtime_emits_component_binding_contract(self):
        source = render_to_string("gerador/snippets/advanced_pages_runtime.txt", {"advanced_pages": {"pages": [self.page()]}})
        compile(source, "advanced_pages.py", "exec")
        self.assertIn('"runtime_key": "advanced_component_status"', source)
        self.assertIn('"binding_field": "status"', source)
        self.assertIn("_component_allowed", source)
        self.assertIn("_load_component_data", source)
