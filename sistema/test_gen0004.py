from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .compiler import SpecificationCompiler
from .models import Entidade, Modulo, Sistema
from .runtime_validation import validate_generated_runtime
from .specification import build_specification

User = get_user_model()


class Gen0004RuntimeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gen0004", password="secret123")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema Runtime GEN-0004",
        )

    def _spec_with_crud(self):
        modulo = Modulo.objects.create(
            sistema=self.sistema,
            nome="Gestão de Pessoas",
        )
        Entidade.objects.create(
            modulo=modulo,
            nome="Funcionário",
            gerar_crud_views=True,
        )
        return build_specification(self.sistema)

    def test_generated_project_runtime_contract_is_valid(self):
        spec = self._spec_with_crud()
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            SpecificationCompiler(spec).write(root)
            templates = validate_generated_runtime(spec, root)

        self.assertIn("gestao_de_pessoas/templates/gestao_de_pessoas/funcionario_list.html", templates)
        self.assertIn("gestao_de_pessoas/templates/gestao_de_pessoas/funcionario_form.html", templates)
        self.assertIn("gestao_de_pessoas/templates/gestao_de_pessoas/funcionario_confirm_delete.html", templates)

    def test_runtime_validation_detects_missing_crud_template(self):
        spec = self._spec_with_crud()
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            SpecificationCompiler(spec).write(root)
            missing = root / "gestao_de_pessoas/templates/gestao_de_pessoas/funcionario_list.html"
            missing.unlink()

            with self.assertRaises(ValidationError) as context:
                validate_generated_runtime(spec, root)

        self.assertIn("Template de runtime ausente", str(context.exception))
        self.assertIn("funcionario_list.html", str(context.exception))

    def test_runtime_validation_detects_broken_crud_url_contract(self):
        spec = self._spec_with_crud()
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            SpecificationCompiler(spec).write(root)
            urls = root / "gestao_de_pessoas/urls.py"
            content = urls.read_text(encoding="utf-8")
            urls.write_text(content.replace('name="funcionario_delete"', 'name="funcionario_remove"'), encoding="utf-8")

            with self.assertRaises(ValidationError) as context:
                validate_generated_runtime(spec, root)

        self.assertIn("funcionario_delete", str(context.exception))
