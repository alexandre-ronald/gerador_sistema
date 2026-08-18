from __future__ import annotations

from pathlib import Path

from django.core.exceptions import ValidationError

from .specification import SystemSpec
from .specification_plan import CompilationPlan


REQUIRED_PACKAGE_FILES = ("manage.py", "requirements.txt", "README.md", ".gitignore")


def validate_generated_package(specification: SystemSpec, root: str | Path) -> tuple[str, ...]:
    """Validate that a generated project is self-describing and installable."""
    root = Path(root).resolve()
    errors: list[str] = []

    if not root.is_dir():
        raise ValidationError(f"Diretório do projeto gerado não existe: {root}")

    plan = CompilationPlan(specification)
    planned = set(plan.paths())

    for filename in REQUIRED_PACKAGE_FILES:
        path = root / filename
        if filename not in planned:
            errors.append(f"Artefato de pacote não previsto no plano: {filename}")
        if not path.is_file():
            errors.append(f"Arquivo essencial de pacote ausente: {filename}")
        elif not path.read_text(encoding="utf-8").strip():
            errors.append(f"Arquivo essencial de pacote vazio: {filename}")

    requirements = root / "requirements.txt"
    if requirements.is_file():
        content = requirements.read_text(encoding="utf-8")
        if "Django" not in content:
            errors.append("requirements.txt não declara Django.")

    readme = root / "README.md"
    if readme.is_file():
        content = readme.read_text(encoding="utf-8")
        for marker in ("pip install -r requirements.txt", "python manage.py migrate", "python manage.py runserver"):
            if marker not in content:
                errors.append(f"README.md não documenta o comando obrigatório: {marker}")

    if errors:
        raise ValidationError(errors)
    return REQUIRED_PACKAGE_FILES
