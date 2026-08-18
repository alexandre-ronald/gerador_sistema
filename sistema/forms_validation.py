from __future__ import annotations

import ast
from pathlib import Path

from django.core.exceptions import ValidationError

from .specification import SystemSpec


class GeneratedFormsValidator:
    """Validate the ModelForm contract of a generated Django project."""

    def __init__(self, specification: SystemSpec, root: str | Path):
        self.specification = specification
        self.root = Path(root).resolve()

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        validated: list[str] = []

        if not self.root.is_dir():
            raise ValidationError(f"Diretório do projeto gerado não existe: {self.root}")

        for module in self.specification.modules:
            forms_path = self.root / module.technical_name / "forms.py"
            if not forms_path.is_file():
                errors.append(f"forms.py ausente: {module.technical_name}/forms.py")
                continue

            try:
                tree = ast.parse(forms_path.read_text(encoding="utf-8"), filename=str(forms_path))
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                errors.append(f"forms.py inválido em {module.technical_name}: {exc}")
                continue

            classes = {
                node.name: node
                for node in tree.body
                if isinstance(node, ast.ClassDef)
            }

            for entity in module.entities:
                form_name = f"{entity.class_name}Form"
                node = classes.get(form_name)
                if node is None:
                    errors.append(
                        f"ModelForm ausente para {module.technical_name}.{entity.class_name}: {form_name}"
                    )
                    continue

                if not self._inherits_from_model_form(node):
                    errors.append(
                        f"Formulário {form_name} não herda de forms.ModelForm."
                    )
                    continue

                meta = self._meta_class(node)
                if meta is None:
                    errors.append(f"Formulário {form_name} não possui classe Meta.")
                    continue

                model_name = self._assignment_name(meta, "model")
                if model_name != entity.class_name:
                    errors.append(
                        f"Formulário {form_name} aponta para model incorreto: {model_name or '<ausente>'}."
                    )

                fields_value = self._assignment_string(meta, "fields")
                if fields_value != "__all__":
                    errors.append(
                        f"Formulário {form_name} deve declarar fields = \"__all__\"."
                    )

                validated.append(f"{module.technical_name}.{form_name}")

        if errors:
            raise ValidationError(errors)

        return tuple(validated)

    @staticmethod
    def _inherits_from_model_form(node: ast.ClassDef) -> bool:
        for base in node.bases:
            if isinstance(base, ast.Attribute):
                if isinstance(base.value, ast.Name) and base.value.id == "forms" and base.attr == "ModelForm":
                    return True
            elif isinstance(base, ast.Name) and base.id == "ModelForm":
                return True
        return False

    @staticmethod
    def _meta_class(node: ast.ClassDef) -> ast.ClassDef | None:
        for child in node.body:
            if isinstance(child, ast.ClassDef) and child.name == "Meta":
                return child
        return None

    @staticmethod
    def _assignment(meta: ast.ClassDef, name: str) -> ast.expr | None:
        for node in meta.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        return node.value
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == name:
                    return node.value
        return None

    @classmethod
    def _assignment_name(cls, meta: ast.ClassDef, name: str) -> str | None:
        value = cls._assignment(meta, name)
        return value.id if isinstance(value, ast.Name) else None

    @classmethod
    def _assignment_string(cls, meta: ast.ClassDef, name: str) -> str | None:
        value = cls._assignment(meta, name)
        return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def validate_generated_forms(specification: SystemSpec, root: str | Path) -> tuple[str, ...]:
    return GeneratedFormsValidator(specification, root).validate()
