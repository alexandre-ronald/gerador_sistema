from __future__ import annotations

from pathlib import Path


class ArtifactWriter:
    """Writes compiler artifacts inside one controlled output directory."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def path(self, relative_path: str) -> Path:
        target = (self.root / relative_path).resolve()
        if target != self.root and self.root not in target.parents:
            raise ValueError(f"Caminho de artefato fora do diretório de saída: {relative_path}")
        return target

    def write(self, relative_path: str, content: str) -> Path:
        target = self.path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        return target
