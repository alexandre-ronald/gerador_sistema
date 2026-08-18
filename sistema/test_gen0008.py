from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model

from .compiler import SpecificationCompiler
from .models import Entidade, Modulo, Sistema
from .package_validation import validate_generated_package
from .specification import build_specification


User = get_user_model()


class Gen0008PackageValidationTests(TestCase):
    def _project(self):
        user = User.objects.create_user(username="gen0008", password="secret123")
        sistema = Sistema.objects.create(usuario=user, nome="Sistema Pacote GEN-0008")
        modulo = Modulo.objects.create(sistema=sistema, nome="Cadastro")
        Entidade.objects.create(modulo=modulo, nome="Pessoa")
        return build_specification(sistema)

    def test_generated_project_has_package_files(self):
        spec = self._project()
        with TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            SpecificationCompiler(spec).write(root)
            result = validate_generated_package(spec, root)
        self.assertEqual(set(result), {"manage.py", "requirements.txt", "README.md", ".gitignore"})

    def test_package_validation_detects_missing_requirements(self):
        spec = self._project()
        with TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            SpecificationCompiler(spec).write(root)
            (root / "requirements.txt").unlink()
            with self.assertRaises(ValidationError) as ctx:
                validate_generated_package(spec, root)
        self.assertIn("requirements.txt", str(ctx.exception))

    def test_package_validation_detects_incomplete_readme(self):
        spec = self._project()
        with TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            SpecificationCompiler(spec).write(root)
            (root / "README.md").write_text("# Projeto", encoding="utf-8")
            with self.assertRaises(ValidationError) as ctx:
                validate_generated_package(spec, root)
        self.assertIn("README.md", str(ctx.exception))
