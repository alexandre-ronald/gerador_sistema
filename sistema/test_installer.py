from types import SimpleNamespace

from django.test import SimpleTestCase

from sistema.installer_views import _installer_content


class InstallerGenerationTests(SimpleTestCase):
    def test_postgresql_installer_has_utf8_and_database_prompts(self):
        sistema = SimpleNamespace(
            nome="Sistema de Eleição",
            banco_dados="postgresql",
            get_banco_dados_display=lambda: "PostgreSQL",
        )

        content = _installer_content(sistema)

        self.assertIn("chcp 65001", content)
        self.assertIn("POSTGRES_DB", content)
        self.assertIn("POSTGRES_USER", content)
        self.assertIn("POSTGRES_PASSWORD", content)
        self.assertIn("POSTGRES_HOST", content)
        self.assertIn("POSTGRES_PORT", content)
        self.assertIn(".env", content)
        self.assertIn("pip install -r requirements.txt", content)
        self.assertIn("python manage.py check", content)
        self.assertIn("python manage.py migrate", content)
        self.assertNotIn("Salvador:", content)

    def test_sqlite_installer_does_not_require_postgres(self):
        sistema = SimpleNamespace(
            nome="Sistema SQLite",
            banco_dados="sqlite3",
            get_banco_dados_display=lambda: "SQLite",
        )

        content = _installer_content(sistema)

        self.assertIn("Banco SQLite selecionado", content)
        self.assertNotIn("POSTGRES_DB", content)
        self.assertNotIn("POSTGRES_PASSWORD", content)
        self.assertIn("python manage.py migrate", content)

    def test_installer_uses_declared_requirements(self):
        sistema = SimpleNamespace(
            nome="Sistema",
            banco_dados="mysql",
            get_banco_dados_display=lambda: "MySQL",
        )

        content = _installer_content(sistema)

        self.assertIn("requirements.txt", content)
        self.assertIn("MYSQL_DATABASE", content)
        self.assertIn("MYSQL_PASSWORD", content)
