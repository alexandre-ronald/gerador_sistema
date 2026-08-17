from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase

from .artifact_writer import ArtifactWriter
from .compiler import SpecificationCompiler
from .models import Campo, Entidade, Modulo, Sistema
from .specification import build_specification


class Gen0003CompilerTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="gen0003")
        self.sistema = Sistema.objects.create(
            usuario=user,
            nome="Sistema de Teste",
            descricao="Teste do compilador",
            banco_dados="sqlite3",
            gerar_docker=True,
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Gestão de Pessoas")
        entidade = Entidade.objects.create(
            modulo=modulo,
            nome="Ordem de Serviço",
            gerar_crud_views=True,
        )
        Campo.objects.create(
            entidade=entidade,
            nome="Descrição",
            tipo="CharField",
            max_length=120,
            blank=True,
        )

    def test_compiler_writes_every_planned_artifact(self):
        spec = build_specification(self.sistema)
        with tempfile.TemporaryDirectory() as tmp:
            result = SpecificationCompiler(spec, tmp).compile()
            self.assertEqual(result.specification_fingerprint, spec.fingerprint)
            self.assertTrue(result.artifacts)
            for relative_path in result.artifacts:
                self.assertTrue((Path(tmp) / relative_path).exists(), relative_path)

    def test_generated_project_passes_django_check(self):
        spec = build_specification(self.sistema)
        with tempfile.TemporaryDirectory() as tmp:
            SpecificationCompiler(spec, tmp).compile()
            result = subprocess.run(
                [sys.executable, "manage.py", "check"],
                cwd=tmp,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generated_models_use_python_safe_names(self):
        spec = build_specification(self.sistema)
        with tempfile.TemporaryDirectory() as tmp:
            SpecificationCompiler(spec, tmp).compile()
            models = Path(tmp, "gestao_de_pessoas", "models.py").read_text(encoding="utf-8")
            self.assertIn("class OrdemDeServico(models.Model):", models)
            self.assertIn("descricao = models.CharField", models)

    def test_artifact_writer_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = ArtifactWriter(tmp)
            with self.assertRaises(ValueError):
                writer.write("../fora.py", "x")
