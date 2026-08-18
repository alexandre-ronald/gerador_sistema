from __future__ import annotations

import re
from pathlib import Path

from django.core.exceptions import ValidationError

from .specification import SystemSpec
from .specification_plan import CompilationPlan


class GeneratedProjectQualityValidator:
    """Perform final quality checks on a compiled project tree."""

    _TEMPLATE_PATTERNS = (
        re.compile(r"render\([^\n]*?[\"']([^\"']+\.html)[\"']"),
        re.compile(r"template_name\s*=\s*[\"']([^\"']+\.html)[\"']"),
    )
    _FORBIDDEN_MARKERS = ("Salvador:", "TODO: GERAR", "PLACEHOLDER")
    _ALLOWED_EMPTY_ARTIFACTS = {
        "__init__.py",
        "migrations/__init__.py",
    }

    def __init__(self, specification: SystemSpec, root: str | Path):
        self.specification = specification
        self.root = Path(root).resolve()

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        plan = CompilationPlan(self.specification)
        artifacts = plan.artifacts()
        paths = [item.path for item in artifacts]

        if len(paths) != len(set(paths)):
            duplicates = sorted({p for p in paths if paths.count(p) > 1})
            errors.append(f"Artefatos duplicados no plano: {', '.join(duplicates)}")

        if not self.root.is_dir():
            raise ValidationError(f"Diretório do projeto gerado não existe: {self.root}")

        for artifact in artifacts:
            path = self.root / artifact.path
            if not path.is_file():
                errors.append(f"Artefato ausente na validação de qualidade: {artifact.path}")
                continue
            if (
                artifact.kind != "static"
                and path.stat().st_size == 0
                and artifact.path not in self._ALLOWED_EMPTY_ARTIFACTS
            ):
                errors.append(f"Artefato vazio: {artifact.path}")

        for html_path in self.root.rglob("*.html"):
            try:
                content = html_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"HTML ilegível em {html_path.relative_to(self.root)}: {exc}")
                continue
            if not content.strip():
                errors.append(f"Template HTML vazio: {html_path.relative_to(self.root)}")
            if "{% extends" not in content and html_path.name not in {"base.html", "login.html"}:
                errors.append(
                    f"Template CRUD sem herança de base.html: {html_path.relative_to(self.root)}"
                )

        for py_path in self.root.rglob("*.py"):
            try:
                content = py_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"Python ilegível em {py_path.relative_to(self.root)}: {exc}")
                continue
            for marker in self._FORBIDDEN_MARKERS:
                if marker in content:
                    errors.append(
                        f"Marcador residual '{marker}' em {py_path.relative_to(self.root)}"
                    )
            for pattern in self._TEMPLATE_PATTERNS:
                for template_name in pattern.findall(content):
                    candidates = [
                        # Project-level Django templates.
                        self.root / "templates" / template_name,
                    ]
                    # App templates follow Django's conventional layout:
                    # <app>/templates/<app>/<template>.html. Resolve the app
                    # from the first component of the template reference rather
                    # than depending on the current Python file's parent.
                    parts = Path(template_name).parts
                    if len(parts) > 1:
                        app_name = parts[0]
                        relative_template = Path(*parts[1:])
                        candidates.append(
                            self.root / app_name / "templates" / app_name / relative_template
                        )
                    # Also support the direct app template layout used by
                    # some generated projects: <app>/templates/<template>.html.
                    if len(parts) > 1:
                        candidates.append(
                            self.root / parts[0] / "templates" / Path(*parts[1:])
                        )

                    if not any(candidate.is_file() for candidate in candidates):
                        errors.append(
                            f"Template referenciado mas não encontrado: {template_name} "
                            f"(em {py_path.relative_to(self.root)})"
                        )

        static_dir = self.root / "static"
        if not static_dir.is_dir():
            errors.append("Diretório static ausente no projeto gerado.")

        if errors:
            raise ValidationError(errors)

        return tuple(paths)


def validate_generated_quality(
    specification: SystemSpec,
    root: str | Path,
) -> tuple[str, ...]:
    return GeneratedProjectQualityValidator(specification, root).validate()
