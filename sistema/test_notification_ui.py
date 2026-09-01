from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class DesignerNotificationUiTests(SimpleTestCase):
    def _source(self, relative_path):
        return (Path(settings.BASE_DIR) / relative_path).read_text(encoding="utf-8")

    def test_form_designer_uses_professional_notification(self):
        source = self._source("sistema/templates/sistema/form_designer.html")
        self.assertIn("forge-notify", source)
        self.assertIn("Alterações salvas", source)
        self.assertNotIn("alert(", source)

    def test_dashboard_designer_uses_professional_notification(self):
        source = self._source("sistema/templates/sistema/dashboard_builder.html")
        self.assertIn("forge-notify", source)
        self.assertIn("Dashboard salvo", source)
        self.assertNotIn("alert(", source)

    def test_model_designer_uses_professional_notification(self):
        source = self._source("templates/sistema/editor.html")
        self.assertIn("forge-notify", source)
        self.assertIn("Projeto salvo", source)
        self.assertNotIn("alert(", source)

    def test_designers_show_saving_state(self):
        for path in (
            "sistema/templates/sistema/form_designer.html",
            "sistema/templates/sistema/dashboard_builder.html",
            "templates/sistema/editor.html",
        ):
            with self.subTest(path=path):
                source = self._source(path)
                self.assertIn("spinner-border", source)
                self.assertIn("Salvando", source)
