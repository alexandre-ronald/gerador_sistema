from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .advanced_page_generation import prepare_advanced_pages_generation
from .runtime_contracts import can_component, can_page


class BusinessExperienceEndToEndTests(SimpleTestCase):
    """Gate transversal do caso de referência da GEN-071.

    Prova que uma única configuração declarativa da Central do Fornecedor
    atravessa geração, runtime relacional e enforcement sem código específico
    de Fornecedor/Contrato no gerador.
    """

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
                self._field("fornecedor", "fornecedor", "ForeignKey"),
                self._field("valor", "valor", "DecimalField"),
                self._field("numero", "numero", "CharField"),
            ],
        )
        return fornecedor, contrato

    def _page(self):
        relation = {"source": "page_context", "source_field": "pk", "target_field": "fornecedor"}
        return {
            "id": "central_fornecedor",
            "name": "Central do Fornecedor",
            "slug": "fornecedor/central",
            "enabled": True,
            "context": {"kind": "record", "entity": "Fornecedor"},
            "navigation": {"visible": False, "label": "", "icon": "", "group": "", "order": 0},
            "components": [
                {
                    "id": "contratos_ativos", "type": "metric", "title": "Contratos ativos",
                    "layout": {"x": 0, "y": 0, "w": 4, "h": 1},
                    "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "",
                    "config": {"relation": relation, "aggregate": {"operation": "count", "field": ""}},
                },
                {
                    "id": "total_contratado", "type": "metric", "title": "Total contratado",
                    "layout": {"x": 4, "y": 0, "w": 4, "h": 1},
                    "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "",
                    "config": {"relation": relation, "aggregate": {"operation": "sum", "field": "valor"}},
                },
                {
                    "id": "contratos", "type": "table", "title": "Contratos do fornecedor",
                    "layout": {"x": 0, "y": 1, "w": 12, "h": 3},
                    "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "",
                    "config": {"relation": relation},
                },
                {
                    "id": "novo_contrato_btn", "type": "button", "title": "Novo contrato",
                    "layout": {"x": 0, "y": 4, "w": 3, "h": 1},
                    "binding": {"kind": "none", "ref": "", "field": ""}, "action": "novo_contrato", "config": {},
                },
            ],
            "actions": [{
                "id": "novo_contrato", "kind": "crud", "label": "Novo contrato",
                "target": {"entity": "Contrato", "operation": "create"},
                "transport": {"source": "page_context", "source_field": "pk", "target_field": "fornecedor"},
            }],
        }

    def _rbac(self, *, contrato_list=True, contrato_create=True):
        contrato_actions = ["view"]
        if contrato_list:
            contrato_actions.append("list")
        if contrato_create:
            contrato_actions.append("create")
        return {
            "enabled": True,
            "roles": [{"id": "gestor", "label": "Gestor", "description": "", "group": "Gestor", "order": 0}],
            "entities": {
                "Fornecedor": {"roles": {"gestor": ["view"]}, "transitions": {}},
                "Contrato": {"roles": {"gestor": contrato_actions}, "transitions": {}},
            },
            "reports": {},
        }

    def test_central_contract_compiles_complete_business_experience(self):
        pages = prepare_advanced_pages_generation({"version": 1, "pages": [self._page()]}, entities=list(self._entities()))
        generated = pages["pages"][0]
        components = {item["id"]: item for item in generated["components"]}
        self.assertEqual(components["contratos_ativos"]["aggregate_runtime"]["operation"], "count")
        self.assertEqual(components["total_contratado"]["aggregate_runtime"]["operation"], "sum")
        self.assertEqual(components["total_contratado"]["aggregate_runtime"]["field_code"], "valor")
        self.assertEqual(components["contratos"]["relation_runtime"]["target_field_code"], "fornecedor")
        action = generated["actions"][0]
        self.assertEqual(action["transport_runtime"]["query_param"], "_ap_context_fornecedor")
        self.assertEqual(action["transport_runtime"]["target_field_code"], "fornecedor")

    def test_generated_runtime_contains_relational_execution_and_context_transport(self):
        pages = prepare_advanced_pages_generation({"version": 1, "pages": [self._page()]}, entities=list(self._entities()))
        runtime = render_to_string("gerador/snippets/advanced_pages_runtime.txt", {"advanced_pages": pages})
        compile(runtime, "advanced_pages.py", "exec")
        self.assertIn('model._default_manager.filter(**{field_name: advanced_record.pk})', runtime)
        self.assertIn('return queryset.count()', runtime)
        self.assertIn('queryset.aggregate(value=aggregate_class(field_name)).get("value")', runtime)
        self.assertIn('"transport_query_param": "_ap_context_fornecedor"', runtime)
        self.assertIn('urlencode({transport_param: advanced_record.pk})', runtime)

    def test_generated_form_receives_only_declared_supplier_context(self):
        fornecedor, contrato = self._entities()
        contrato.form_designer_ready = False
        pages = prepare_advanced_pages_generation({"version": 1, "pages": [self._page()]}, entities=[fornecedor, contrato])
        form = render_to_string(
            "gerador/snippets/html_form.txt",
            {"advanced_pages": pages, "entidade": contrato, "app_name": "compras"},
        )
        self.assertIn("_ap_context_fornecedor", form)
        self.assertIn("field:'fornecedor'", form)
        self.assertIn("transportedBindings.forEach", form)

    def test_rbac_keeps_page_but_hides_related_data_without_list(self):
        page = self._page()
        self.assertTrue(can_page(self._rbac(contrato_list=False), "gestor", page).allowed)
        metric = next(item for item in page["components"] if item["id"] == "contratos_ativos")
        table = next(item for item in page["components"] if item["id"] == "contratos")
        self.assertFalse(can_component(self._rbac(contrato_list=False), "gestor", page, metric).allowed)
        self.assertFalse(can_component(self._rbac(contrato_list=False), "gestor", page, table).allowed)

    def test_rbac_hides_contextual_create_without_create_grant(self):
        page = self._page()
        button = next(item for item in page["components"] if item["id"] == "novo_contrato_btn")
        self.assertFalse(can_component(self._rbac(contrato_create=False), "gestor", page, button).allowed)
        self.assertTrue(can_component(self._rbac(), "gestor", page, button).allowed)
