import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.template.loader import get_template

from sistema.models import Campo
from sistema.runtime_validation import validate_generated_runtime
from sistema.services import GeradorService


BASE_TEMPLATE = """<!doctype html>
<html>
<body>
    {% if request.resolver_match.app_name %}
    {% if perms.cadastro.view_pessoa %}
    <a href=\"{% url 'cadastro:pessoa_list' %}\">Pessoa</a>
    {% endif %}
    {% endif %}
    <a href=\"{% url 'login' %}\">Entrar</a>
    <form action=\"{% url 'logout' %}\" method=\"post\">{% csrf_token %}</form>
    {% block content %}{% endblock %}
</body>
</html>
"""


class GeneratedRuntimeValidationTests(SimpleTestCase):
    def _create_project(self):
        root = Path(tempfile.mkdtemp(prefix="django_generated_test_"))
        (root / "templates" / "registration").mkdir(parents=True)
        (root / "demo").mkdir()
        (root / "manage.py").write_text(
            """import os\nimport sys\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo.settings')\nfrom django.core.management import execute_from_command_line\nexecute_from_command_line(sys.argv)\n""",
            encoding="utf-8",
        )
        (root / "requirements.txt").write_text("Django>=5.2,<7\n", encoding="utf-8")
        (root / "demo" / "__init__.py").write_text("", encoding="utf-8")
        (root / "demo" / "settings.py").write_text(
            """SECRET_KEY = 'test'\nDEBUG = True\nROOT_URLCONF = 'demo.urls'\nALLOWED_HOSTS = []\nINSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes']\nDATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}\nTEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': ['templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': []}}]\nMIDDLEWARE = []\nUSE_TZ = True\n""",
            encoding="utf-8",
        )
        (root / "demo" / "urls.py").write_text(
            """from django.contrib.auth.decorators import login_required\nfrom django.http import HttpResponse\nfrom django.urls import include, path\n\n@login_required\ndef view(request):\n    return HttpResponse('ok')\n\nurlpatterns = [\n    path('', view, name='index'),\n    path('accounts/', include('django.contrib.auth.urls')),\n]\n""",
            encoding="utf-8",
        )
        (root / "demo" / "wsgi.py").write_text("import os\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo.settings')\n", encoding="utf-8")
        (root / "templates" / "base.html").write_text(BASE_TEMPLATE, encoding="utf-8")
        (root / "templates" / "index.html").write_text("{% extends 'base.html' %}{% block content %}OK{% endblock %}", encoding="utf-8")
        (root / "templates" / "registration" / "login.html").write_text("Login", encoding="utf-8")
        return root

    def test_valid_generated_project_passes(self):
        root = self._create_project()
        result = validate_generated_runtime(root)
        self.assertGreater(result["checked"], 0)
        self.assertTrue(any("Django system check" in msg for msg in result["messages"]))

    def test_invalid_template_is_rejected(self):
        root = self._create_project()
        (root / "templates" / "index.html").write_text("{% if broken %}", encoding="utf-8")
        with self.assertRaises(ValidationError) as ctx:
            validate_generated_runtime(root)
        self.assertIn("Template inválido", str(ctx.exception))

    def test_authentication_contract_is_required(self):
        root = self._create_project()
        (root / "templates" / "base.html").write_text("{% block content %}{% endblock %}", encoding="utf-8")
        with self.assertRaises(ValidationError) as ctx:
            validate_generated_runtime(root)
        self.assertIn("Contrato do template base incompleto", str(ctx.exception))

    def test_generator_base_snippet_is_valid_django_template(self):
        template = get_template("gerador/snippets/base_html.txt")
        self.assertIsNotNone(template)

    def test_campo_exposes_relational_contract(self):
        self.assertFalse(Campo(tipo="CharField").eh_relacional)
        self.assertTrue(Campo(tipo="ForeignKey").eh_relacional)
        self.assertTrue(Campo(tipo="OneToOneField").eh_relacional)
        self.assertTrue(Campo(tipo="ManyToManyField").eh_relacional)

    def test_python_identifier_never_returns_keyword(self):
        for value in ["class", "from", "import", "for", "while", "def"]:
            identifier = GeradorService._python_identifier(value)
            self.assertNotEqual(identifier, value)
            self.assertTrue(identifier.isidentifier())

    def test_class_name_removes_accents_without_corrupting_the_word(self):
        cases = {
            "Funcionário": "Funcionario",
            "Eleição": "Eleicao",
            "Órgão": "Orgao",
            "Seção": "Secao",
            "Município": "Municipio",
            "Área de Gestão": "AreaDeGestao",
        }
        for original, expected in cases.items():
            self.assertEqual(GeradorService._class_name(original), expected)

    def test_class_name_does_not_generate_legacy_funcionrio_form(self):
        self.assertEqual(GeradorService._class_name("Funcionário"), "Funcionario")
        self.assertNotEqual(GeradorService._class_name("Funcionário"), "FuncionRio")


class MultiDatabaseSettingsSnippetTests(SimpleTestCase):
    def _render_settings(self, banco_dados):
        from django.template.loader import render_to_string
        from types import SimpleNamespace
        sistema = SimpleNamespace(nome="Sistema de Teste", banco_dados=banco_dados)
        modulo = SimpleNamespace(app_name="app_teste")
        return render_to_string("gerador/snippets/settings.txt", {"sistema": sistema, "nome_projeto": "sistema_de_teste", "modulos": [modulo]})

    def test_sqlite_settings_contains_engine_and_name(self):
        content = self._render_settings("sqlite3")
        self.assertIn("django.db.backends.sqlite3", content)
        self.assertIn("db.sqlite3", content)
        self.assertIn("ENGINE", content)

    def test_postgresql_settings_contains_engine_and_env(self):
        content = self._render_settings("postgresql")
        self.assertIn("django.db.backends.postgresql", content)
        self.assertIn("POSTGRES_DB", content)
        self.assertIn("sistema_de_teste_db", content)
        self.assertNotIn("sistema-de-teste_db", content)

    def test_mysql_settings_contains_engine(self):
        content = self._render_settings("mysql")
        self.assertIn("django.db.backends.mysql", content)
        self.assertIn("MYSQL_DATABASE", content)

    def test_sqlserver_settings_contains_engine(self):
        content = self._render_settings("sqlserver")
        self.assertIn("'ENGINE': 'mssql'", content)
        self.assertIn("MSSQL_DATABASE", content)

    def test_oracle_settings_contains_engine(self):
        content = self._render_settings("oracle")
        self.assertIn("django.db.backends.oracle", content)