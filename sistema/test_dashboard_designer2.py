from django.test import SimpleTestCase

from .builder_contracts import normalize_dashboard_config, normalize_widget


class DashboardDesigner2ContractTests(SimpleTestCase):
    def test_legacy_widget_receives_default_appearance(self):
        widget = normalize_widget({
            "id": "legacy",
            "type": "metric",
            "title": "Legado",
            "entity": "Pedido",
            "x": 2,
            "y": 1,
            "w": 4,
            "h": 3,
            "config": {"operation": "count"},
        })
        self.assertEqual(widget["x"], 2)
        self.assertEqual(widget["y"], 1)
        self.assertEqual(widget["w"], 4)
        self.assertEqual(widget["h"], 3)
        self.assertEqual(widget["config"]["operation"], "count")
        self.assertEqual(widget["config"]["appearance"], {
            "variant": "default",
            "show_header": True,
            "show_border": True,
            "compact": False,
        })

    def test_custom_appearance_is_preserved(self):
        widget = normalize_widget({
            "config": {"appearance": {
                "variant": "minimal",
                "show_header": False,
                "show_border": False,
                "compact": True,
            }}
        })
        self.assertEqual(widget["config"]["appearance"]["variant"], "minimal")
        self.assertFalse(widget["config"]["appearance"]["show_header"])
        self.assertFalse(widget["config"]["appearance"]["show_border"])
        self.assertTrue(widget["config"]["appearance"]["compact"])

    def test_invalid_variant_falls_back_to_default(self):
        widget = normalize_widget({"config": {"appearance": {"variant": "invalid"}}})
        self.assertEqual(widget["config"]["appearance"]["variant"], "default")

    def test_dashboard_layout_coordinates_remain_unchanged(self):
        config = normalize_dashboard_config({"widgets": [{
            "id": "chart-1", "type": "bar", "x": 6, "y": 4, "w": 6, "h": 5,
        }]})
        widget = config["widgets"][0]
        self.assertEqual((widget["x"], widget["y"], widget["w"], widget["h"]), (6, 4, 6, 5))
