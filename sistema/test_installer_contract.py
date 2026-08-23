from types import SimpleNamespace

from django.test import SimpleTestCase
from django.template.loader import render_to_string

from sistema.installer_views import _installer_content


class InstallerContractTests(SimpleTestCase):
    """Regression tests for the generated Windows installer contract."""

    @staticmethod
    def _system(db_type="postgresql"):
        displays = {
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "sqlserver": "SQL Server",
            "oracle": "Oracle",
            "sqlite3": "SQLite",
        }
        return SimpleNamespace(
            nome="Sistema de Eleição",
            banco_dados=db_type,
            get_banco_dados_display=lambda: displays[db_type],
        )

    def test_postgresql_installer_prompts_for_database_and_creates_env(self):
        content = _installer_content(self._system("postgresql"))
        self.assertIn("set /p \"POSTGRES_DB=Nome do banco", content)
        self.assertIn("set /p \"POSTGRES_USER=Usuario", content)
        self.assertIn("set /p \"POSTGRES_PASSWORD=Senha", content)
        self.assertIn("POSTGRES_HOST", content)
        self.assertIn("POSTGRES_PORT", content)
        self.assertIn("Path('.env').write_text", content)
        self.assertIn("python -m pip install -r requirements.txt", content)
        self.assertNotIn("pip install django django-crispy-forms crispy-bootstrap5 pillow", content)

    def test_installer_is_utf8_safe_and_does_not_emit_old_broken_command(self):
        content = _installer_content(self._system("postgresql"))
        self.assertIn("chcp 65001", content)
        self.assertIn("DisableDelayedExpansion", content)
        self.assertNotIn("Salvador:", content)
        self.assertNotIn("Configuring environment local", content)

    def test_settings_template_declares_python_dotenv_dependency(self):
        sistema = self._system("sqlite3")
        content = render_to_string(
            "gerador/snippets/settings.txt",
            {"sistema": sistema, "nome_projeto": "sistema_teste", "modulos": []},
        )
        self.assertIn("from dotenv import load_dotenv", content)
        self.assertIn("python-dotenv", "python-dotenv>=1.0")
