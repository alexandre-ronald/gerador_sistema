from django.contrib.auth import get_user_model
from django.test import TestCase

from .builder_contracts import normalize_dashboard_config


class DashboardBuilderQueryDesignerTests(TestCase):
    def test_widget_query_defaults_are_present(self):
        config = normalize_dashboard_config({"widgets": [{"type": "bar", "entity": "Pessoa"}]})
        query = config["widgets"][0]["config"]
        self.assertEqual(query["operation"], "count")
        self.assertEqual(query["field"], "id")
        self.assertEqual(query["limit"], 100)
        self.assertIn("group_by", query)
        self.assertIn("group_by_related", query)

    def test_widget_query_is_normalized(self):
        config = normalize_dashboard_config({"widgets": [{"type": "table", "config": {"operation": "sum", "field": "valor", "fields": ["id", "nome"], "limit": 25}}]})
        query = config["widgets"][0]["config"]
        self.assertEqual(query["operation"], "sum")
        self.assertEqual(query["fields"], ["id", "nome"])
        self.assertEqual(query["limit"], 25)

    def test_invalid_operation_falls_back_to_count(self):
        config = normalize_dashboard_config({"widgets": [{"config": {"operation": "sql_injection"}}]})
        self.assertEqual(config["widgets"][0]["config"]["operation"], "count")
