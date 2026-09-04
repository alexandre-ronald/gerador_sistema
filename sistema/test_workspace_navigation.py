from types import SimpleNamespace

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

    def test_system_list_is_project_home_not_system_workspace(self):
        source = render_to_string("sistema/lista.html", {"sistemas": []})

        self.assertIn("Meus Sistemas", source)
        self.assertIn(
            "As ferramentas de Design, Build e Run ficam organizadas dentro do Workspace",
            source,
        )
        self.assertIn("Relatórios", source)
        self.assertIn("Novo sistema", source)
        self.assertNotIn("DjangoForge Workspace", source)

    def test_system_workspace_exposes_lifecycle_areas(self):
        sistema = SimpleNamespace(
            id=1,
            pk=1,
            nome="Sistema de Teste",
            descricao="Projete, valide, publique e acompanhe esta aplicação.",
            gerar_docker=False,
            get_banco_dados_display=lambda: "SQLite",
        )
        source = render_to_string(
            "sistema/workspace.html",
            {
                "sistema": sistema,
                "total_modulos": 0,
                "total_entidades": 0,
            },
        )

        self.assertIn("Workspace do sistema", source)
        self.assertIn("Projete, valide, publique e acompanhe", source)
        self.assertIn(">Design<", source)
        self.assertIn(">Build<", source)
        self.assertIn(">Run<", source)
        self.assertIn(">Govern<", source)
        self.assertIn("Model Designer", source)
        self.assertIn("Report Designer", source)
        self.assertIn("Crie um ou vários relatórios", source)
        self.assertIn("/reports/", source)
        self.assertIn("Validation Center", source)
        self.assertIn("Deployment Center", source)
        self.assertIn("Meus Sistemas", source)
