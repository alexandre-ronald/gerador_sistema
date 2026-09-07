from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .advanced_page_generation import prepare_advanced_pages_generation


class RelationalGeneratedRuntimeTests(SimpleTestCase):
    def _field(self, name, code, field_type):
        return SimpleNamespace(nome=name, codigo_nome=code, verbose_nome=name, tipo=field_type)

    def _entities(self):
        module = SimpleNamespace(app_name="compras")
        fornecedor = SimpleNamespace(
            nome="Fornecedor",
            codigo_nome="fornecedor",
            classe_nome="Fornecedor",
            modulo=module,
            campos_geracao=[self._field("nome", "nome", "CharField")],
        )
        contrato = SimpleNamespace(
            nome="Contrato",
            codigo_nome="contrato",
            classe_nome="Contrato",
            modulo=module,
            campos_geracao=[
                self._field("fornecedor responsável", "fornecedor_responsavel", "ForeignKey"),
                self._field("valor total", "valor_total", "DecimalField"),
                self._field("numero", "numero", "CharField"),
            ],
        )
        return fornecedor, contrato

    def _config(self):
        relation = {"source": "page_context", "source_field": "pk", "target_field": "fornecedor responsável"}
        return {
            "version": 1,
            "pages": [{
                "id": "central_fornecedor",
                "name": "Central do Fornecedor",
                "slug": "fornecedor/central",
                "enabled": True,
                "context": {"kind": "record", "entity": "Fornecedor"},
                "navigation": {"visible": False, "label": "", "icon": "", "group": "", "order": 0},
                "components": [
                    {
                        "id": "contratos", "type": "table", "title": "Contratos",
                        "layout": {"x": 0, "y": 0, "w": 12, "h": 3},
                        "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "",
                        "config": {"relation": relation},
                    },
                    {
                        "id": "total", "type": "metric", "title": "Total contratado",
                        "layout": {"x": 0, "y": 3, "w": 4, "h": 1},
                        "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "",
                        "config": {"relation": relation, "aggregate": {"operation": "sum", "field": "valor total"}},
                    },
                    {
                        "id": "novo", "type": "button", "title": "Novo contrato",
                        "layout": {"x": 0, "y": 4, "w": 3, "h": 1},
                        "binding": {"kind": "none", "ref": "", "field": ""}, "action": "novo_contrato", "config": {},
                    },
                ],
                "actions": [{
                    "id": "novo_contrato", "kind": "crud", "label": "Novo contrato",
                    "target": {"entity": "Contrato", "operation": "create"},
                    "transport": {"source": "page_context", "source_field": "pk", "target_field": "fornecedor responsável"},
                }],
            }],
        }

    def test_generation_translates_contract_field_names_to_python_codes(self):
        pages = prepare_advanced_pages_generation(self._config(), entities=list(self._entities()))
        page = pages["pages"][0]
        components = {item["id"]: item for item in page["components"]}
        self.assertEqual(components["contratos"]["relation_runtime"]["target_field_code"], "fornecedor_responsavel")
        self.assertEqual(components["total"]["aggregate_runtime"]["field_code"], "valor_total")
        action = page["actions"][0]
        self.assertEqual(action["transport_runtime"]["target_field_code"], "fornecedor_responsavel")
        self.assertEqual(action["transport_runtime"]["query_param"], "_ap_context_fornecedor_responsavel")

    def test_generated_runtime_filters_aggregates_and_transports_context(self):
        pages = prepare_advanced_pages_generation(self._config(), entities=list(self._entities()))
        source = render_to_string("gerador/snippets/advanced_pages_runtime.txt", {"advanced_pages": pages})
        compile(source, "advanced_pages.py", "exec")
        self.assertIn('"relation_target_field": "fornecedor_responsavel"', source)
        self.assertIn('"aggregate_operation": "sum"', source)
        self.assertIn('"aggregate_field": "valor_total"', source)
        self.assertIn('model._default_manager.filter(**{field_name: advanced_record.pk})', source)
        self.assertIn('queryset.aggregate(value=aggregate_class(field_name)).get("value")', source)
        self.assertIn('"transport_query_param": "_ap_context_fornecedor_responsavel"', source)
        self.assertIn('urlencode({transport_param: advanced_record.pk})', source)

    def test_generated_form_only_accepts_compiled_transport_bindings(self):
        fornecedor, contrato = self._entities()
        contrato.form_designer_ready = False
        pages = prepare_advanced_pages_generation(self._config(), entities=[fornecedor, contrato])
        source = render_to_string(
            "gerador/snippets/html_form.txt",
            {"advanced_pages": pages, "entidade": contrato, "app_name": "compras"},
        )
        self.assertIn("_ap_context_fornecedor_responsavel", source)
        self.assertIn("field:'fornecedor_responsavel'", source)
        self.assertIn("transportedBindings.forEach", source)
        self.assertIn("CSS.escape(binding.field)", source)
