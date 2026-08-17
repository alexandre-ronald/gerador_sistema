from __future__ import annotations

import ast
from pathlib import Path

from django.core.exceptions import ValidationError

from .specification import SystemSpec
from .specification_plan import CompilationPlan


class GeneratedProjectValidator:
    """Validate a generated project before it is exported to the user."""

    def __init__(self, specification: SystemSpec, root: str | Path):
        self.specification = specification
        self.root = Path(root).resolve()

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        plan = CompilationPlan(self.specification)

        if not self.root.is_dir():
            raise ValidationError(
                f"Diretório do projeto gerado não existe: {self.root}"
            )

        for artifact in plan.artifacts():
            path = self.root / artifact.path
            if not path.is_file():
                errors.append(f"Artefato ausente: {artifact.path}")

        for path in self.root.rglob("*.py"):
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                errors.append(f"Python inválido em {path.relative_to(self.root)}: {exc}")

        settings_path = self.root / f"{self.specification.technical_name}/settings.py"
        if settings_path.is_file():
            settings = settings_path.read_text(encoding="utf-8")
            for module in self.specification.modules:
                if f'"{module.technical_name}"' not in settings:
                    errors.append(
                        f"Módulo técnico ausente no INSTALLED_APPS: {module.technical_name}"
                    )
                if f'"{module.name}"' in settings and "-" in module.name:
                    errors.append(
                        f"Nome humano usado como identificador de app: {module.name}"
                    )

        urls_path = self.root / f"{self.specification.technical_name}/urls.py"
        if urls_path.is_file():
            urls = urls_path.read_text(encoding="utf-8")
            for module in self.specification.modules:
                expected = f'include("{module.technical_name}.urls")'
                if expected not in urls:
                    errors.append(
                        f"Include técnico ausente em urls.py: {module.technical_name}"
                    )

        if errors:
            raise ValidationError(errors)

        return tuple(item.path for item in plan.artifacts())


def validate_generated_project(
    specification: SystemSpec,
    root: str | Path,
) -> tuple[str, ...]:
    return GeneratedProjectValidator(specification, root).validate()
