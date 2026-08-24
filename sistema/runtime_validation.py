import ast
import os
import re
import subprocess
import sys
from pathlib import Path

from django.core.exceptions import ValidationError
from django.template import Engine, TemplateSyntaxError


class GeneratedProjectRuntimeValidator:
    """Fail-fast validation for the generated project contract."""

    REQUIRED_ROOT_FILES = (
        "manage.py",
        "templates/base.html",
        "templates/index.html",
        "templates/registration/login.html",
        "requirements.txt",
    )

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.errors = []
        self.warnings = []
        self.checked = 0
        self._loggable = []

    def validate(self):
        if not self.root.exists():
            raise ValidationError([f"Diretório gerado não existe: {self.root}"])
        self._validate_required_files()
        self._validate_python_files()
        self._validate_templates()
        self._validate_navigation_contract()
        self._validate_dependency_contract()
        self._validate_django_check()
        if self.errors:
            raise ValidationError(self.errors)
        return {"checked": self.checked, "warnings": list(self.warnings), "messages": list(self._loggable)}

    def _message(self, message):
        self._loggable.append(message)

    def _validate_required_files(self):
        missing = [path for path in self.REQUIRED_ROOT_FILES if not (self.root / path).is_file()]
        if missing:
            self.errors.append("Arquivos obrigatórios ausentes: " + ", ".join(missing))
            return
        self.checked += len(self.REQUIRED_ROOT_FILES)
        self._message("✅ Estrutura obrigatória do projeto validada")

    def _validate_python_files(self):
        valid = 0
        for path in sorted(self.root.rglob("*.py")):
            if any(part in {".venv", "__pycache__"} for part in path.parts):
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                valid += 1
                self.checked += 1
            except (SyntaxError, UnicodeDecodeError) as exc:
                self.errors.append(f"Python inválido em {path.relative_to(self.root)}: {exc}")
        self._message(f"✅ Sintaxe Python validada ({valid} arquivo(s))")

    def _validate_templates(self):
        engine = Engine(debug=False)
        valid = 0
        for path in sorted(self.root.rglob("*.html")):
            if any(part in {".venv", "__pycache__"} for part in path.parts):
                continue
            try:
                engine.from_string(path.read_text(encoding="utf-8"))
                valid += 1
                self.checked += 1
            except (TemplateSyntaxError, UnicodeDecodeError) as exc:
                self.errors.append(f"Template inválido em {path.relative_to(self.root)}: {exc}")
        self._message(f"✅ Templates Django validados ({valid} arquivo(s))")

    def _validate_navigation_contract(self):
        base = self.root / "templates" / "base.html"
        index = self.root / "templates" / "index.html"
        context_processors = list(self.root.glob("*/context_processors.py"))
        settings_files = list(self.root.glob("*/settings.py"))
        if not context_processors:
            self.errors.append("Contrato de navegação incompleto: context processor não foi gerado")
            return
        if not settings_files:
            self.errors.append("Contrato de navegação incompleto: settings.py não foi localizado")
            return

        base_content = base.read_text(encoding="utf-8")
        index_content = index.read_text(encoding="utf-8")
        nav_content = context_processors[0].read_text(encoding="utf-8")
        settings_content = settings_files[0].read_text(encoding="utf-8")

        required = {
            "navegação centralizada": "navigation_modules",
            "namespace seguro": "request.resolver_match.app_name",
            "URL dinâmica": "url item.url_name",
            "permissão de navegação": "data-permission=\"{{ item.permission }}\"",
            "login": "{% url 'login' %}",
            "logout": "{% url 'logout' %}",
            "proteção CSRF": "{% csrf_token %}",
            "bloco content": "{% block content %}",
        }
        missing = [name for name, token in required.items() if token not in base_content]
        if "navigation_modules" not in index_content:
            missing.append("navegação do index")
        for token in ("NAVIGATION_MODULES", "has_perm", "def navigation", "url_name", "permission"):
            if token not in nav_content:
                missing.append(f"context processor: {token}")
        if "context_processors.navigation" not in settings_content:
            missing.append("registro do context processor")

        if missing:
            self.errors.append("Contrato de navegação incompleto: " + ", ".join(missing))
            return
        self.checked += len(required) + 5
        self._message("✅ Contrato único de navegação, URLs e permissões validado")

    def _read_requirements(self):
        path = self.root / "requirements.txt"
        names = set()
        if not path.is_file():
            return names
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[<>=!~;\[]", line, maxsplit=1)[0].strip().lower()
            if name:
                names.add(name)
        return names

    def _validate_dependency_contract(self):
        requirements = self._read_requirements()
        settings_files = list(self.root.glob("*/settings.py"))
        if not settings_files:
            self.errors.append("Arquivo settings.py do projeto gerado não foi localizado")
            return
        content = settings_files[0].read_text(encoding="utf-8")
        missing = []
        if "from dotenv import load_dotenv" in content and "python-dotenv" not in requirements:
            missing.append("python-dotenv")
        backends = {
            "django.db.backends.postgresql": "psycopg",
            "django.db.backends.mysql": "mysqlclient",
            "django.db.backends.oracle": "oracledb",
            "'mssql'": "mssql-django",
        }
        for backend, dependency in backends.items():
            if backend in content and dependency not in requirements:
                missing.append(dependency)
        if missing:
            self.errors.append("Dependências ausentes em requirements.txt: " + ", ".join(missing))
            return
        self.checked += 1
        self._message("✅ Contrato de dependências e settings validado")

    def _validate_django_check(self):
        manage = self.root / "manage.py"
        if not manage.is_file():
            return
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("DJANGO_SETTINGS_MODULE", None)
        env["PYTHONPATH"] = str(self.root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        try:
            result = subprocess.run(
                [sys.executable, str(manage), "check"], cwd=self.root, env=env,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.errors.append(f"Não foi possível executar 'manage.py check': {exc}")
            return
        if result.returncode != 0:
            output = (result.stdout + "\n" + result.stderr).strip()
            missing_driver = any(token in output for token in (
                "Error loading psycopg2 or psycopg module", "Error loading MySQLdb module",
                "No module named 'MySQLdb'", "No module named 'oracledb'",
                "No module named 'mssql'", "No module named 'dotenv'",
            ))
            if missing_driver:
                self.warnings.append(
                    "Django system check foi adiado porque uma dependência externa do projeto gerado "
                    "não está instalada no ambiente do gerador. O requirements.txt contém a dependência."
                )
                self._message("⚠️ Django system check adiado: dependência externa ausente")
                return
            self.errors.append(f"Django system check falhou: {output[-4000:]}")
            return
        self.checked += 1
        self._message("✅ Django system check executado com sucesso")


def validate_generated_runtime(root):
    return GeneratedProjectRuntimeValidator(root).validate()
