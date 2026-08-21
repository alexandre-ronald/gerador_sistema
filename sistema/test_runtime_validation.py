import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from sistema.runtime_validation import validate_generated_runtime, GeneratedProjectRuntimeValidator


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
        (root / "demo" / "__init__.py").write_text("", encoding="utf-8")
        (root / "demo" / "settings.py").write_text(
            """SECRET_KEY = 'test'\nDEBUG = True\nROOT_URLCONF = 'demo.urls'\nALLOWED_HOSTS = []\nINSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes']\nDATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}\nTEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': ['templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': []}}]\nMIDDLEWARE = []\nUSE_TZ = True\n""",
            encoding="utf-8",
        )
        (root / "demo" / "urls.py").write_text(
            """from django.urls import path\nfrom django.http import HttpResponse\n\ndef view(request):\n    return HttpResponse('ok')\n\nurlpatterns = [path('', view, name='index'), path('login/', view, name='login'), path('logout/', view, name='logout')]\n""",
            encoding="utf-8",
        )
        (root / "demo" / "wsgi.py").write_text(
            """import os\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo.settings')\n""",
            encoding="utf-8",
        )
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
        (root / "templates" / "base.html").write_text(
            "{% block content %}{% endblock %}", encoding="utf-8"
        )

        with self.assertRaises(ValidationError) as ctx:
            validate_generated_runtime(root)

        self.assertIn("Contrato do template base incompleto", str(ctx.exception))

    def test_module_permissions_are_required_when_crud_navigation_exists(self):
        root = self._create_project()
        (root / "templates" / "base.html").write_text(
            "{% if request.resolver_match.app_name %}"
            "<a href=\"{% url 'cadastro:pessoa_list' %}\">Pessoa</a>"
            "{% endif %}"
            "{% url 'login' %}{% url 'logout' %}"
            "{% csrf_token %}{% block content %}{% endblock %}",
            encoding="utf-8",
        )

        with self.assertRaises(ValidationError) as ctx:
            validate_generated_runtime(root)

        self.assertIn("permissões de módulo", str(ctx.exception))

    def test_module_permissions_accept_generated_permission_expression(self):
        root = self._create_project()
        (root / "templates" / "base.html").write_text(
            "{% if request.resolver_match.app_name %}"
            "{% if perms.cadastro.view_pessoa %}"
            "<a href=\"{% url 'cadastro:pessoa_list' %}\">Pessoa</a>"
            "{% endif %}{% endif %}"
            "{% url 'login' %}{% url 'logout' %}"
            "{% csrf_token %}{% block content %}{% endblock %}",
            encoding="utf-8",
        )

        validator = GeneratedProjectRuntimeValidator(root)
        validator._validate_runtime_contract()

        self.assertNotIn("permissões de módulo", " ".join(validator.errors))

    def test_module_permissions_are_not_required_without_crud_navigation(self):
        root = self._create_project()
        (root / "templates" / "base.html").write_text(
            "{% if request.resolver_match.app_name %}Dashboard{% endif %}"
            "{% url 'login' %}{% url 'logout' %}"
            "{% csrf_token %}{% block content %}{% endblock %}",
            encoding="utf-8",
        )

        validator = GeneratedProjectRuntimeValidator(root)
        validator._validate_runtime_contract()

        self.assertNotIn("permissões de módulo", " ".join(validator.errors))
