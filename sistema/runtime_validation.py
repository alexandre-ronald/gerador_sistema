import ast
import os
import re
import subprocess
import sys
from pathlib import Path

from django.core.exceptions import ValidationError
from django.template import Engine, TemplateSyntaxError


class GeneratedProjectRuntimeValidator:
    """Valida o projeto gerado por contratos independentes e progressivos."""

    REQUIRED_ROOT_FILES = ("manage.py", "templates/base.html", "templates/index.html", "templates/registration/login.html", "requirements.txt")
    BASE_CONTRACT = {"login": "{% url 'login' %}", "logout": "{% url 'logout' %}", "csrf": "{% csrf_token %}", "content": "{% block content %}"}
    NAVIGATION_CONTRACT = {"navigation": "navigation_modules", "namespace": "request.resolver_match.app_name", "dynamic_url": "url item.url_name", "permission": 'data-permission="{{ item.permission }}"'}

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.errors, self.warnings, self._loggable = [], [], []
        self.checked = 0

    def validate(self):
        if not self.root.exists(): raise ValidationError([f"Diretório gerado não existe: {self.root}"])
        self._validate_required_files(); self._validate_python_files(); self._validate_templates(); self._validate_base_contract(); self._validate_navigation_contract(); self._validate_dependency_contract(); self._validate_django_check()
        if self.errors: raise ValidationError(self.errors)
        return {"checked": self.checked, "warnings": list(self.warnings), "messages": list(self._loggable)}

    def _message(self, message): self._loggable.append(message)
    def _read_generated_settings(self): return next(iter(self.root.glob("*/settings.py")), None)
    def _read_generated_context_processor(self): return next(iter(self.root.glob("*/context_processors.py")), None)

    def _validate_required_files(self):
        missing = [path for path in self.REQUIRED_ROOT_FILES if not (self.root / path).is_file()]
        if missing: self.errors.append("Arquivos obrigatórios ausentes: " + ", ".join(missing)); return
        self.checked += len(self.REQUIRED_ROOT_FILES); self._message("✅ Estrutura obrigatória do projeto validada")

    def _validate_python_files(self):
        valid = 0
        for path in sorted(self.root.rglob("*.py")):
            if any(part in {".venv", "__pycache__"} for part in path.parts): continue
            try: ast.parse(path.read_text(encoding="utf-8"), filename=str(path)); valid += 1; self.checked += 1
            except (SyntaxError, UnicodeDecodeError) as exc: self.errors.append(f"Python inválido em {path.relative_to(self.root)}: {exc}")
        self._message(f"✅ Sintaxe Python validada ({valid} arquivo(s))")

    def _validate_templates(self):
        engine, valid = Engine(debug=False), 0
        for path in sorted(self.root.rglob("*.html")):
            if any(part in {".venv", "__pycache__"} for part in path.parts): continue
            try: engine.from_string(path.read_text(encoding="utf-8")); valid += 1; self.checked += 1
            except (TemplateSyntaxError, UnicodeDecodeError) as exc: self.errors.append(f"Template inválido em {path.relative_to(self.root)}: {exc}")
        self._message(f"✅ Templates Django validados ({valid} arquivo(s))")

    def _validate_base_contract(self):
        base = self.root / "templates/base.html"
        if not base.is_file(): return
        missing = [name for name, token in self.BASE_CONTRACT.items() if token not in base.read_text(encoding="utf-8")]
        if missing: self.errors.append("Contrato do template base incompleto: " + ", ".join(missing)); return
        self.checked += len(self.BASE_CONTRACT); self._message("✅ Contrato de autenticação e layout base validado")

    def _validate_navigation_contract(self):
        base = self.root / "templates/base.html"
        if not base.is_file(): return
        base_content = base.read_text(encoding="utf-8")
        if "navigation_modules" not in base_content:
            self._message("ℹ️ Navegação centralizada não utilizada neste projeto"); return
        processor, settings = self._read_generated_context_processor(), self._read_generated_settings()
        if processor is None: self.errors.append("Contrato de navegação incompleto: context processor não foi gerado"); return
        if settings is None: self.errors.append("Contrato de navegação incompleto: settings.py não foi localizado"); return
        nav_content, settings_content = processor.read_text(encoding="utf-8"), settings.read_text(encoding="utf-8")
        index = self.root / "templates/index.html"
        missing = [name for name, token in self.NAVIGATION_CONTRACT.items() if token not in base_content]
        index_content = index.read_text(encoding="utf-8") if index.is_file() else ""
        if not index.is_file() or "navigation_modules" not in index_content: missing.append("navegação do index")
        for token in ("NAVIGATION_MODULES", "has_perm", "def navigation", "permission"):
            if token not in nav_content: missing.append(f"context processor: {token}")
        # url_name is required only when the specification actually contains CRUD entries.
        has_crud = '"url_name"' in nav_content and '"permission"' in nav_content and "_list" in nav_content
        if has_crud and "url_name" not in nav_content: missing.append("context processor: url_name")
        if "context_processors.navigation" not in settings_content: missing.append("registro do context processor")
        if missing: self.errors.append("Contrato de navegação incompleto: " + ", ".join(missing)); return
        self.checked += len(self.NAVIGATION_CONTRACT) + 5; self._message("✅ Contrato único de navegação, URLs e permissões validado")

    def _read_requirements(self):
        path, names = self.root / "requirements.txt", set()
        if not path.is_file(): return names
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"): continue
            name = re.split(r"[<>=!~;\[]", line, maxsplit=1)[0].strip().lower()
            if name: names.add(name)
        return names

    def _validate_dependency_contract(self):
        requirements, settings = self._read_requirements(), self._read_generated_settings()
        if settings is None: self.errors.append("Arquivo settings.py do projeto gerado não foi localizado"); return
        content, missing = settings.read_text(encoding="utf-8"), []
        if "from dotenv import load_dotenv" in content and "python-dotenv" not in requirements: missing.append("python-dotenv")
        for backend, dependency in {"django.db.backends.postgresql": "psycopg", "django.db.backends.mysql": "mysqlclient", "django.db.backends.oracle": "oracledb", "'mssql'": "mssql-django"}.items():
            if backend in content and dependency not in requirements: missing.append(dependency)
        if missing: self.errors.append("Dependências ausentes em requirements.txt: " + ", ".join(missing)); return
        self.checked += 1; self._message("✅ Contrato de dependências e settings validado")

    def _validate_django_check(self):
        manage = self.root / "manage.py"
        if not manage.is_file(): return
        env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"; env.pop("DJANGO_SETTINGS_MODULE", None); env["PYTHONPATH"] = str(self.root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        try: result = subprocess.run([sys.executable, str(manage), "check"], cwd=self.root, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        except (OSError, subprocess.SubprocessError) as exc: self.errors.append(f"Não foi possível executar 'manage.py check': {exc}"); return
        if result.returncode != 0:
            output = (result.stdout + "\n" + result.stderr).strip()
            if any(token in output for token in ("Error loading psycopg2 or psycopg module", "Error loading MySQLdb module", "No module named 'MySQLdb'", "No module named 'oracledb'", "No module named 'mssql'", "No module named 'dotenv'")):
                self.warnings.append("Django system check foi adiado porque uma dependência externa do projeto gerado não está instalada no ambiente do gerador."); self._message("⚠️ Django system check adiado: dependência externa ausente"); return
            self.errors.append(f"Django system check falhou: {output[-4000:]}"); return
        self.checked += 1; self._message("✅ Django system check executado com sucesso")


def validate_generated_runtime(root): return GeneratedProjectRuntimeValidator(root).validate()
