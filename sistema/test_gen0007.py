from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.test import TestCase

from .compiler import SpecificationCompiler
from .models import Campo, Entidade, Modulo, Sistema
from .quality_validation import validate_generated_quality
from .specification import build_specification
from django.contrib.auth import get_user_model

User = get_user_model()


class Gen0007QualityValidationTests(TestCase):
    def _project(self):
        user = User.objects.create_user(username="gen0007", password="secret123")
        sistema = Sistema.objects.create(usuario=user, nome="Sistema Qualidade GEN-0007")
        modulo = Modulo.objects.create(sistema=sistema, nome="Cadastro")
        entidade = Entidade.objects.create(modulo=modulo, nome="Pessoa", gerar_crud_views=True)
        Campo.objects.create(entidade=entidade, nome="Nome", tipo="CharField", max_length=100)
        return build_specification(sistema)

    def test_generated_project_passes_quality_gate(self):
        spec = self._project()
        with TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            SpecificationCompiler(spec).write(root)
            result = validate_generated_quality(spec, root)
        self.assertTrue(result)

    def test_quality_gate_detects_empty_crud_template(self):
        spec = self._project()
        with TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            SpecificationCompiler(spec).write(root)
            template = root / "cadastro/templates/cadastro/pessoa_list.html"
            template.write_text("", encoding="utf-8")
            with self.assertRaises(ValidationError) as ctx:
                validate_generated_quality(spec, root)
        self.assertIn("Template HTML vazio", str(ctx.exception))

    def test_quality_gate_detects_residual_placeholder(self):
        spec = self._project()
        with TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            SpecificationCompiler(spec).write(root)
            source = root / "cadastro/views.py"
            source.write_text(source.read_text(encoding="utf-8") + "\n# Salvador:\n", encoding="utf-8")
            with self.assertRaises(ValidationError) as ctx:
                validate_generated_quality(spec, root)
        self.assertIn("Marcador residual 'Salvador:'", str(ctx.exception))
