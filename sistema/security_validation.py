from __future__ import annotations

from pathlib import Path
import re

from django.core.exceptions import ValidationError


FORBIDDEN_PATTERNS = (
    re.compile(r"SECRET_KEY\s*=\s*['\"](?:django-insecure-)?[^'\"]+['\"]"),
    re.compile(r"PASSWORD\s*=\s*['\"]\S+['\"]", re.I),
    re.compile(r"API_KEY\s*=\s*['\"]\S+['\"]", re.I),
)


def validate_generated_security(root: Path) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []

    if not root.exists():
        raise ValidationError(f"Diretório de geração não encontrado: {root}")

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".txt", ".md", ".bat", ".env", ".yml", ".yaml"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"Arquivo não UTF-8: {path.relative_to(root)}")
            continue

        relative = path.relative_to(root).as_posix()
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(content):
                errors.append(f"Possível segredo embutido em {relative}")

        if "DEBUG = True" in content or "DEBUG=True" in content:
            errors.append(f"DEBUG=True não permitido em artefato distribuível: {relative}")

        if "ALLOWED_HOSTS = ['*']" in content or 'ALLOWED_HOSTS = ["*"]' in content:
            errors.append(f"ALLOWED_HOSTS aberto não permitido: {relative}")

    if errors:
        raise ValidationError(errors)
    return [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
