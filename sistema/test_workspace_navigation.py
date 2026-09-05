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
        self.assertIn("Application Preview Studio", source)
        self.assertIn("/preview-studio/", source)
        self.assertIn("bi-window-stack", source)
        self.assertIn("Model Designer", source)
        self.assertIn("Report Designer", source)
        self.assertIn("Crie um ou vários relatórios", source)
        self.assertIn("/reports/", source)
        self.assertIn("Validation Center", source)
        self.assertIn("Deployment Center", source)
        self.assertIn("Gerar aplicação", source)
        self.assertIn("Backup Manager e AI Copilot", source)
        self.assertIn("Meus Sistemas", source)

    def test_application_blueprint_links_back_to_specialized_designers(self):
        sistema = SimpleNamespace(id=1, pk=1, nome="Sistema de Teste")
        source = render_to_string(
            "sistema/application_blueprint.html",
            {
                "sistema": sistema,
                "inventory": {},
                "blueprint": {
                    "application": {"name": "Sistema de Teste"},
                    "modules": [],
                    "information": [],
                    "relationships": [],
                    "experiences": [],
                    "dashboard": {"enabled": False, "widgets": []},
                    "processes": [],
                    "responsibilities": [],
                    "readiness": {"coverage": [], "issues": []},
                },
            },
        )

        self.assertIn("Continuar no Designer", source)
        self.assertIn("/editar/", source)
        self.assertIn("/form-designer/", source)
        self.assertIn("/crud-designer/", source)
        self.assertIn("/reports/", source)
        self.assertIn("/dashboard-builder/", source)
        self.assertIn("/workflow/", source)
        self.assertIn("/permissions/", source)
        self.assertIn("/validation-center/", source)
        self.assertIn("bi-diagram-3", source)
        self.assertIn("bi-ui-checks-grid", source)
        self.assertIn("bi-table", source)
        self.assertIn("bi-file-earmark-bar-graph", source)
        self.assertIn("bi-grid-1x2", source)
        self.assertIn("bi-bezier2", source)
        self.assertIn("bi-shield-lock", source)
        self.assertIn("bi-shield-check", source)
