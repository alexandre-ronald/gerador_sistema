from __future__ import annotations

from pathlib import Path

from django.core.exceptions import ValidationError
from django.template import Engine, TemplateSyntaxError

from .specification import SystemSpec


class GeneratedProjectRuntimeValidator:
    """Validate the runtime-facing contract of a generated Django project."""

    def __init__(self, specification: SystemSpec, root: str | Path):
        self.specification = specification
        self.root = Path(root).resolve()

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []

        if not self.root.is_dir():
            raise ValidationError(f"Diretório do projeto gerado não existe: {self.root}")

        errors.extend(self._validate_templates())
        errors.extend(self._validate_views())
        errors.extend(self._validate_urls())

        if errors:
            raise ValidationError(errors)

        return tuple(self._expected_runtime_templates())

    def _expected_runtime_templates(self) -> list[str]:
        result = ["templates/base.html", "templates/index.html", "templates/registration/login.html"]
        for module in self.specification.modules:
            for entity in module.entities:
                if not entity.generate_crud:
                    continue
                base = f"{module.technical_name}/templates/{module.technical_name}"
                result.extend(
                    [
                        f"{base}/{entity.technical_name}_list.html",
                        f"{base}/{entity.technical_name}_form.html",
                        f"{base}/{entity.technical_name}_confirm_delete.html",
                    ]
                )
        return result

    def _validate_templates(self) -> list[str]:
        errors: list[str] = []
        for relative in self._expected_runtime_templates():
            path = self.root / relative
            if not path.is_file():
                errors.append(f"Template de runtime ausente: {relative}")
                continue
            try:
                Engine(debug=False).from_string(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, TemplateSyntaxError) as exc:
                errors.append(f"Template inválido em {relative}: {exc}")
        return errors

    def _validate_views(self) -> list[str]:
        errors: list[str] = []
        for module in self.specification.modules:
            path = self.root / module.technical_name / "views.py"
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            for entity in module.entities:
                if not entity.generate_crud:
                    continue
                expected = {
                    "list": f'{module.technical_name}/{entity.technical_name}_list.html',
                    "form": f'{module.technical_name}/{entity.technical_name}_form.html',
                    "delete": f'{module.technical_name}/{entity.technical_name}_confirm_delete.html',
                }
                for kind, template in expected.items():
                    if template not in content:
                        errors.append(
                            f"View {module.technical_name}.{entity.class_name} não referencia o template de {kind}: {template}"
                        )
        return errors

    def _validate_urls(self) -> list[str]:
        errors: list[str] = []
        for module in self.specification.modules:
            path = self.root / module.technical_name / "urls.py"
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            for entity in module.entities:
                if not entity.generate_crud:
                    continue
                expected_names = (
                    f'name="{entity.technical_name}_list"',
                    f'name="{entity.technical_name}_create"',
                    f'name="{entity.technical_name}_update"',
                    f'name="{entity.technical_name}_delete"',
                )
                for expected in expected_names:
                    if expected not in content:
                        errors.append(
                            f"URL CRUD ausente para {module.technical_name}.{entity.class_name}: {expected}"
                        )
        return errors


def validate_generated_runtime(specification: SystemSpec, root: str | Path) -> tuple[str, ...]:
    return GeneratedProjectRuntimeValidator(specification, root).validate()
