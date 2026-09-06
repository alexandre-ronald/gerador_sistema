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
                    {"id": "editar", "type": "button", "title": "Editar", "layout": {"x": 4, "y": 1, "w": 4, "h": 1}, "binding": {"kind": "none", "ref": "", "field": ""}, "action": "editar_contrato", "config": {}},
                    {"id": "relatorio", "type": "link", "title": "Relatório", "layout": {"x": 8, "y": 1, "w": 4, "h": 1}, "binding": {"kind": "none", "ref": "", "field": ""}, "action": "abrir_relatorio", "config": {}},
                    {"id": "detalhe", "type": "record_detail", "title": "Dados", "layout": {"x": 0, "y": 2, "w": 12, "h": 2}, "binding": {"kind": "page_context", "ref": "", "field": ""}, "action": "", "config": {}},
                    {"id": "tabela", "type": "table", "title": "Contratos", "layout": {"x": 0, "y": 4, "w": 12, "h": 3}, "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "", "config": {}},
                    {"id": "formulario", "type": "form", "title": "Editar contrato", "layout": {"x": 0, "y": 7, "w": 12, "h": 3}, "binding": {"kind": "form", "ref": "Contrato", "field": ""}, "action": "", "config": {}},
                    {"id": "report_block", "type": "report", "title": "Relatório geral", "layout": {"x": 0, "y": 10, "w": 6, "h": 2}, "binding": {"kind": "report", "ref": "Contrato", "field": ""}, "action": "", "config": {"report_id": "geral"}},
                    {"id": "dashboard_block", "type": "dashboard", "title": "Painel", "layout": {"x": 6, "y": 10, "w": 6, "h": 2}, "binding": {"kind": "dashboard", "ref": "dashboard", "field": ""}, "action": "", "config": {}},
                    {"id": "aprovar", "type": "workflow_action", "title": "Aprovar", "layout": {"x": 0, "y": 12, "w": 4, "h": 1}, "binding": {"kind": "workflow", "ref": "Contrato", "field": ""}, "action": "aprovar_contrato", "config": {}},
                ],
                "actions": [
                    {"id": "editar_contrato", "kind": "crud", "label": "Editar contrato", "target": {"entity": "Contrato", "operation": "update"}},
                    {"id": "abrir_relatorio", "kind": "report", "label": "Relatório geral", "target": {"entity": "Contrato", "report": "geral"}},
                    {"id": "aprovar_contrato", "kind": "workflow", "label": "Aprovar contrato", "target": {"entity": "Contrato", "transition": "aprovar"}},
                ],
            }],
        }

    def page(self):
        return prepare_advanced_pages_generation(self.config(), entities=[self.entity()])["pages"][0]

    def test_generation_adds_field_and_runtime_metadata(self):
        page = self.page()
        status = page["components"][1]
        detail = page["components"][4]
        self.assertEqual(status["runtime_key"], "advanced_component_status")
        self.assertEqual(status["binding_field"]["code"], "status")
        self.assertEqual([field["code"] for field in detail["binding_fields"]], ["numero", "status"])

    def test_generation_projects_crud_report_and_workflow_actions(self):
        page = self.page()
        actions = {action["id"]: action for action in page["actions"]}
        self.assertEqual(actions["editar_contrato"]["url_name"], "contratos:contrato_update")
        self.assertTrue(actions["editar_contrato"]["requires_pk"])
        self.assertEqual(actions["abrir_relatorio"]["url_name"], "contratos:contrato_report_geral")
        self.assertEqual(actions["aprovar_contrato"]["url_name"], "contratos:contrato_transition")
        self.assertTrue(actions["aprovar_contrato"]["requires_pk"])
        self.assertEqual(page["components"][2]["runtime_action"]["id"], "editar_contrato")

    def test_generation_projects_form_report_and_dashboard_components(self):
        page = self.page()
        form = page["components"][6]
        report = page["components"][7]
        dashboard = page["components"][8]
        self.assertEqual(form["form_class_name"], "ContratoForm")
        self.assertEqual(form["native_operation"], "update")
        self.assertTrue(form["native_requires_pk"])
        self.assertEqual(report["report_id"], "geral")
        self.assertEqual(report["native_url_name"], "contratos:contrato_report_geral")
        self.assertEqual(dashboard["native_url_name"], "dashboard")

    def test_generated_page_template_is_valid_django_template(self):
        source = render_to_string("gerador/snippets/advanced_page_html.txt", {"page": self.page()})
        Template(source)
        self.assertIn("advanced_component_status_visible", source)
        self.assertIn("{{ advanced_component_status }}", source)
        self.assertIn("{% for row in advanced_component_tabela %}", source)
        self.assertIn("{{ row.numero }}", source)
        self.assertIn("{{ advanced_component_editar_action_url }}", source)
        self.assertIn("Editar contrato", source)
        self.assertIn('name="_advanced_form_component" value="formulario"', source)
        self.assertIn("{% for field in advanced_component_formulario.visible_fields %}", source)
        self.assertIn("{{ advanced_component_report_block_native_url }}", source)
        self.assertIn("{{ advanced_component_dashboard_block_native_url }}", source)
        self.assertIn('<form method="post" action="{{ advanced_component_aprovar_action_url }}"', source)
        self.assertIn("Aprovar contrato", source)
        self.assertIn("grid-template-columns:repeat(12", source)

    def test_runtime_emits_component_binding_and_action_contract(self):
        source = render_to_string("gerador/snippets/advanced_pages_runtime.txt", {"advanced_pages": {"pages": [self.page()]}})
        compile(source, "advanced_pages.py", "exec")
        self.assertIn('"runtime_key": "advanced_component_status"', source)
        self.assertIn('"binding_field": "status"', source)
        self.assertIn('"operation": "update"', source)
        self.assertIn('"report": "geral"', source)
        self.assertIn('"transition": "aprovar"', source)
        self.assertIn('"form_class_name": "ContratoForm"', source)
        self.assertIn('"native_operation": "update"', source)
        self.assertIn("_action_allowed", source)
        self.assertIn("_action_url", source)
        self.assertIn("_build_form_component", source)
        self.assertIn("apply_initial_state", source)
        self.assertIn("run_business_rules", source)
        self.assertIn("can_report", source)
        self.assertIn("can_transition", source)
