from django.template.loader import render_to_string
from django.test import SimpleTestCase


class WorkspaceNavigationTemplateTests(SimpleTestCase):
    def test_settings_is_djangoforge_page(self):
        source = render_to_string("sistema/settings.html")
        self.assertIn("DjangoForge Platform", source)
        self.assertIn("Mapa de configurações", source)
        self.assertNotIn("AdminPanel", source)

    def test_analytics_is_djangoforge_page_without_fake_kpis(self):
        source = render_to_string("sistema/analytics.html")
        self.assertIn("DjangoForge Insights", source)
        self.assertIn("Fontes de relatório", source)
        self.assertNotIn("48.290", source)
        self.assertNotIn("340", source)
        self.assertNotIn("AdminPanel", source)

    def test_system_workspace_exposes_lifecycle_areas(self):
        source = render_to_string("sistema/lista.html", {"sistemas": []})
        self.assertIn("DjangoForge Workspace", source)
        self.assertIn("Projete, valide, publique e acompanhe", source)
        self.assertIn("Design, Build e Run", source)
        self.assertIn("Relatórios", source)
        self.assertIn("Configurações", source)
        self.assertIn("Novo sistema", source)
