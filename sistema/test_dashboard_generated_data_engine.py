from django.template.loader import render_to_string
from django.test import SimpleTestCase


class GeneratedDashboardDataEngineTests(SimpleTestCase):
    def render(self, widgets=None):
        return render_to_string("gerador/snippets/dashboard_data_views.txt", {
            "dashboard_json": __import__("json").dumps(widgets or []),
        })

    def test_generated_runtime_has_safe_query_contract(self):
        source = self.render()
        self.assertIn("ALLOWED_OPERATIONS = {'count', 'sum', 'avg', 'min', 'max'}", source)
        self.assertIn("MAX_LIMIT = 500", source)
        self.assertIn("if not name or '__' in name", source)
        self.assertIn("return max(1, min(MAX_LIMIT, value))", source)

    def test_generated_runtime_supports_all_aggregations(self):
        source = self.render()
        self.assertIn("'count': Count", source)
        self.assertIn("'sum': Sum", source)
        self.assertIn("'avg': Avg", source)
        self.assertIn("'min': Min", source)
        self.assertIn("'max': Max", source)
        self.assertIn("AGGREGATES[operation](field_name)", source)

    def test_generated_runtime_supports_table_fields_ordering_and_limit(self):
        source = self.render()
        self.assertIn("config.get('fields')", source)
        self.assertIn("config.get('ordering')", source)
        self.assertIn("qs = qs.order_by(ordering)", source)
        self.assertIn("qs.values(*fields)[:limit]", source)

    def test_generated_runtime_supports_related_grouping(self):
        source = self.render()
        self.assertIn("config.get('group_by_related')", source)
        self.assertIn("config.get('related_label')", source)
        self.assertIn("return f'{related}__{label}'", source)

    def test_generated_runtime_isolates_widget_errors(self):
        source = self.render()
        self.assertIn("for widget in widgets:", source)
        self.assertIn("except Exception:", source)
        self.assertIn("item['error'] = 'Não foi possível executar a consulta deste widget.'", source)
        self.assertIn("result.append(item)", source)

    def test_widget_json_is_embedded_without_changing_visual_contract(self):
        widget = {"id": "w1", "type": "metric", "entity": "Pedido", "x": 8, "y": 3, "w": 4, "h": 2, "config": {"operation": "sum", "field": "valor_total"}}
        source = self.render([widget])
        self.assertIn('"operation": "sum"', source)
        self.assertIn('"field": "valor_total"', source)
        self.assertIn('"x": 8', source)
        self.assertIn('"w": 4', source)
