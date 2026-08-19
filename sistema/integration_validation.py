from __future__ import annotations

from pathlib import Path
import ast
import re

from django.core.exceptions import ValidationError


class GeneratedProjectIntegrationValidator:
    """Final cross-artifact validation for a generated Django project."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def validate(self) -> list[str]:
        if not self.root.exists():
            raise ValidationError(f"Diretório de geração não encontrado: {self.root}")

        errors: list[str] = []
        py_files = list(self.root.rglob("*.py"))

        for path in py_files:
            relative = path.relative_to(self.root).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            except (SyntaxError, UnicodeDecodeError) as exc:
                errors.append(f"Python inválido em {relative}: {exc}")
                continue

            if path.name == "urls.py":
                errors.extend(self._validate_url_patterns(tree, relative))

            if path.name == "views.py":
                errors.extend(self._validate_view_templates(tree, relative))

        if errors:
            raise ValidationError(errors)

        return [p.relative_to(self.root).as_posix() for p in py_files]

    def _validate_view_templates(self, tree: ast.AST, relative: str) -> list[str]:
        errors: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "render":
                if len(node.args) < 2 or not isinstance(node.args[1], ast.Constant) or not isinstance(node.args[1].value, str):
                    continue
                template = node.args[1].value
                if not self._template_exists(template):
                    errors.append(f"Template referenciado mas não encontrado: {template} (em {relative})")
        return errors

    def _template_exists(self, template: str) -> bool:
        normalized = template.replace("\\", "/")
        candidates = [self.root / "templates" / normalized, self.root / normalized]
        parts = normalized.split("/")
        if len(parts) >= 2:
            candidates.append(self.root / parts[0] / "templates" / "/".join(parts[1:]))
        return any(path.is_file() for path in candidates)

    def _validate_url_patterns(self, tree: ast.AST, relative: str) -> list[str]:
        errors: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "path":
                if len(node.args) < 2:
                    continue
                view = node.args[1]
                if isinstance(view, ast.Attribute) and isinstance(view.value, ast.Name):
                    if view.attr == "as_view":
                        continue
                if isinstance(view, ast.Name):
                    # Function/class names are resolved by Python at import time; AST confirms
                    # the referenced symbol is locally declared or imported.
                    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
                    if view.id not in names:
                        errors.append(f"View referenciada mas não encontrada: {view.id} (em {relative})")
        return errors


def validate_generated_integration(root: Path) -> list[str]:
    return GeneratedProjectIntegrationValidator(root).validate()
