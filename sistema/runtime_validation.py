import ast
import os
import re
import subprocess
import sys
from pathlib import Path

from django.core.exceptions import ValidationError
from django.template import Engine, TemplateSyntaxError


class GeneratedProjectRuntimeValidator:
    """Validate the generated project before it is reported as compiled."""

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

    def validate(self):
        if not self.root.exists():
            raise ValidationError([f"Diretório gerado não existe: {self.root}"])

        self._loggable = []
        self._validate_required_files()
        self._validate_python_files()
        self._validate_templates()
        self._validate_runtime_contract()
        self._validate_dependency_contract()
        self._validate_django_check()

        if self.errors:
            raise ValidationError(self.errors)

        return {
            "checked": self.checked,
            "warnings": list(self.warnings),
            "messages": list(self._loggable),
        }

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
        files = sorted(self.root.rglob("*.py"))
        valid = 0
        for path in files:
            if any(part in {".venv", "__pycache__"} for part in path.parts):
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                valid += 1
                self.checked += 1
            except (SyntaxError, UnicodeDecodeError) as exc:
                rel = path.relative_to(self.root)
                self.errors.append(f"Python inválido em {rel}: {exc}")

        self._message(f"✅ Sintaxe Python validada ({valid} arquivo(s))")

    def _validate_templates(self):
        html_files = sorted(self.root.rglob("*.html"))
        engine = Engine(debug=False)
        valid = 0

        for path in html_files:
            if any(part in {".venv", "__pycache__"} for part in path.parts):
                continue
            try:
                engine.from_string(path.read_text(encoding="utf-8"))
                valid += 1
                self.checked += 1
            except (TemplateSyntaxError, UnicodeDecodeError) as exc:
                rel = path.relative_to(self.root)
                self.errors.append(f"Template inválido em {rel}: {exc}")

        self._message(f"✅ Templates Django validados ({valid} arquivo(s))")

    def _validate_runtime_contract(self):
        base = self.root / "templates" / "base.html"
        if not base.is_file():
            return

        content = base.read_text(encoding="utf-8")
        contracts = {
            "navegação por app": "request.resolver_match.app_name",
            "permissões de módulo": "perms.",
            "login": "{% url 'login' %}",
            "logout": "{% url 'logout' %}",
            "proteção CSRF": "{% csrf_token %}",
            "bloco content": "{% block content %}",
        }

        missing = [name for name, token in contracts.items() if token not in content]
        if missing:
            self.errors.append("Contrato do template base incompleto: " + ", ".join(missing))
            return

        self.checked += len(contracts)
        self._message("✅ Contrato de navegação, permissões e autenticação validado")

    def _read_requirements(self):
        path = self.root / "requirements.txt"
        if not path.is_file():
            return set()
        names = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[<>=!~;\[]", line, maxsplit=1)[0].strip().lower()
            if name:
                names.add(name)
        return names

    def _validate_dependency_contract(self):
        """Ensure settings imports have their runtime dependencies in requirements."""
        requirements = self._read_requirements()
        settings = self.root / "*"
        settings_files = list(self.root.glob("*/settings.py"))
        if not settings_files:
            self.errors.append("Arquivo settings.py do projeto gerado não foi localizado")
            return

        content = settings_files[0].read_text(encoding="utf-8")
        missing = []

        if "from dotenv import load_dotenv" in content and "python-dotenv" not in requirements:
            missing.append("python-dotenv (usado por settings.py)")

        backend_dependencies = {
            "django.db.backends.postgresql": "psycopg",
            "django.db.backends.mysql": "mysqlclient",
            "django.db.backends.oracle": "oracledb",
            "'mssql'": "mssql-django",
        }
        for backend, dependency in backend_dependencies.items():
            if backend in content and dependency not in requirements:
                missing.append(f"{dependency} (backend {backend})")

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

        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(self.root) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")

        try:
            result = subprocess.run(
                [sys.executable, str(manage), "check"],
                cwd=self.root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.errors.append(f"Não foi possível executar 'manage.py check': {exc}")
            return

        if result.returncode != 0:
            output = (result.stdout + "\n" + result.stderr).strip()
            missing_driver = (
                "Error loading psycopg2 or psycopg module" in output
                or "Error loading MySQLdb module" in output
                or "No module named 'MySQLdb'" in output
                or "No module named 'oracledb'" in output
                or "No module named 'mssql'" in output
                or "No module named 'dotenv'" in output
            )
            if missing_driver:
                warning = (
                    "Django system check não pôde abrir o banco porque uma dependência do projeto "
                    "gerado ainda não está instalada no ambiente do gerador. O projeto gerado contém "
                    "o requirements.txt correspondente. Execute 'python -m pip install -r requirements.txt' "
                    "no projeto gerado antes de executar migrate/runserver."
                )
                self.warnings.append(warning)
                self._message("⚠️ Django system check adiado: dependência externa ausente no ambiente atual")
                return

            self.errors.append(f"Django system check falhou: {output[-4000:]}")
            return

        self.checked += 1
        self._message("✅ Django system check executado com sucesso")


def validate_generated_runtime(root):
    return GeneratedProjectRuntimeValidator(root).validate()
