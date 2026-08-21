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
    )

    MODULE_CRUD_URL_RE = re.compile(
        r"\{\%\s*url\s+['\"][A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*_list['\"]"
    )

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.errors = []
        self.warnings = []
        self.checked = 0
        # Runtime-contract tests may invoke individual validation methods
        # directly, without going through validate(). Keep the message
        # collector part of the validator's initialized state rather than
        # creating it only as a side effect of validate().
        self._loggable = []

    def validate(self):
        if not self.root.exists():
            raise ValidationError([f"Diretório gerado não existe: {self.root}"])

        self._loggable = []
        self._validate_required_files()
        self._validate_python_files()
        self._validate_templates()
        self._validate_runtime_contract()
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
            "navegação por app": (
                "request.resolver_match.app_name",
                "request.resolver_match.url_name",
            ),
            "login": ("{% url 'login' %}", "{% templatetag openblock %} url 'login'"),
            "logout": ("{% url 'logout' %}", "{% templatetag openblock %} url 'logout'"),
            "proteção CSRF": ("{% csrf_token %}", "{% templatetag openblock %} csrf_token"),
            "bloco content": ("{% block content %}", "{% templatetag openblock %} block content"),
        }

        missing = [
            name for name, alternatives in contracts.items()
            if not any(token in content for token in alternatives)
        ]

        has_module_crud_navigation = bool(self.MODULE_CRUD_URL_RE.search(content))
        if has_module_crud_navigation and not self._has_module_permission_contract(content):
            missing.append("permissões de módulo")

        if missing:
            self.errors.append("Contrato do template base incompleto: " + ", ".join(missing))
            return

        self.checked += len(contracts) + int(has_module_crud_navigation)
        if has_module_crud_navigation:
            self._message("✅ Contrato de navegação, permissões e autenticação validado")
        else:
            self._message("✅ Contrato de navegação e autenticação validado (sem navegação CRUD de módulos)")

    @staticmethod
    def _has_module_permission_contract(content):
        """Return whether a generated base template guards module CRUD links."""
        permission_patterns = (
            r"\bperms\.[A-Za-z_][A-Za-z0-9_]*\.view_[A-Za-z_][A-Za-z0-9_]*\b",
            r"\bperms\s*\.\s*[A-Za-z_][A-Za-z0-9_]*\s*\.\s*view_[A-Za-z_][A-Za-z0-9_]*\b",
            r"templatetag\s+openblock\s*%\}\s*if\s+perms\.",
        )
        return any(re.search(pattern, content) for pattern in permission_patterns)

    def _validate_django_check(self):
        manage = self.root / "manage.py"
        if not manage.is_file():
            return

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("DJANGO_SETTINGS_MODULE", None)
        env["DB_ENGINE"] = "sqlite3"

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
            self.errors.append(f"Django system check falhou: {output[-4000:]}")
            return

        self.checked += 1
        self._message("✅ Django system check executado com sucesso (validação estrutural com SQLite)")


def validate_generated_runtime(root):
    return GeneratedProjectRuntimeValidator(root).validate()
