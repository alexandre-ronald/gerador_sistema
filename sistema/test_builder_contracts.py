from django.test import SimpleTestCase

from .builder_contracts import (
    CRUD_ACTIONS,
    normalize_crud_config,
    normalize_dashboard_config,
    normalize_theme_config,
    spec_fingerprint,
)


class BuilderContractsTests(SimpleTestCase):
    def test_crud_normalization_keeps_only_supported_actions(self):
        config = normalize_crud_config({"actions": ["list", "create", "invalid"], "page_size": 999})
        self.assertEqual(config["actions"], ["list", "create"])
        self.assertEqual(config["page_size"], 200)
        self.assertEqual(set(config["actions"]), set(CRUD_ACTIONS) & set(config["actions"]))

    def test_theme_normalization_falls_back_to_safe_defaults(self):
        config = normalize_theme_config({"menu": "invalid", "density": "invalid", "dark_mode": "invalid"})
        self.assertEqual(config["menu"], "lateral")
        self.assertEqual(config["density"], "comfortable")
        self.assertEqual(config["dark_mode"], "system")

    def test_dashboard_normalization(self):
        config = normalize_dashboard_config({"widgets": [{"type": "line", "w": 99, "h": 0}]})
        self.assertEqual(config["widgets"][0]["type"], "line")
        self.assertEqual(config["widgets"][0]["w"], 12)
        self.assertEqual(config["widgets"][0]["h"], 1)

    def test_fingerprint_is_deterministic(self):
        self.assertEqual(spec_fingerprint({"b": 2, "a": 1}), spec_fingerprint({"a": 1, "b": 2}))
        self.assertNotEqual(spec_fingerprint({"a": 1}), spec_fingerprint({"a": 2}))
