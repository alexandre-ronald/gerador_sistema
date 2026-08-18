from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .compiler import SpecificationCompiler
from .forms_validation import validate_generated_forms
from .models import Campo, Entidade, Modulo, Sistema
from .specification import build_specification

User = get_user_model()


class Gen0005FormsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gen0005", password="secret123")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema Forms GEN-0005",
        )
        self.modulo = Modulo.objects.create(
            sistema=self.sistema,
            nome="Gestão de Pessoas",
        )
        self.entidade = Entidade.objects.create(
            modulo=self.modulo,
            nome="Funcionário",
            gerar_crud_views=True,
        )
        Campo.objects.create(
            entidade=self.entidade,
            nome="Nome Completo",
            tipo="CharField",
            max_length=150,
            blank=False,
            verbose_name="Nome completo",
            help_text="Informe o nome completo do funcionário.",
        )
        Campo.objects.create(
            entidade=self.entidade,
            nome="CPF",
            tipo="CharField",
            max_length=11,
            unique=True,
        )
        self.spec = build_specification(self.sistema)

    def _compile(self):
        temp_dir = TemporaryDirectory()
        root = Path(temp_dir.name) / "project"
        SpecificationCompiler(self.spec).write(root)
        return temp_dir, root

    def test_forms_contract_is_valid(self):
        temp_dir, root = self._compile()
        try:
            forms = validate_generated_forms(self.spec, root)
        finally:
            temp_dir.cleanup()

        self.assertEqual(forms, ("gestao_de_pessoas.FuncionarioForm",))

    def test_generated_form_points_to_expected_model_and_fields(self):
        temp_dir, root = self._compile()
        try:
            content = (root / "gestao_de_pessoas/forms.py").read_text(encoding="utf-8")
        finally:
            temp_dir.cleanup()

        self.assertIn("class FuncionarioForm(forms.ModelForm):", content)
        self.assertIn("model = Funcionario", content)
        self.assertIn('fields = "__all__"', content)

    def test_validator_detects_wrong_model(self):
        temp_dir, root = self._compile()
        try:
            path = root / "gestao_de_pessoas/forms.py"
            content = path.read_text(encoding="utf-8")
            path.write_text(content.replace("model = Funcionario", "model = OutroModelo"), encoding="utf-8")

            with self.assertRaises(ValidationError) as context:
                validate_generated_forms(self.spec, root)
        finally:
            temp_dir.cleanup()

        self.assertIn("model incorreto", str(context.exception))

    def test_validator_detects_missing_form(self):
        temp_dir, root = self._compile()
        try:
            path = root / "gestao_de_pessoas/forms.py"
            content = path.read_text(encoding="utf-8")
            path.write_text(content.replace("class FuncionarioForm", "class PessoaForm"), encoding="utf-8")

            with self.assertRaises(ValidationError) as context:
                validate_generated_forms(self.spec, root)
        finally:
            temp_dir.cleanup()

        self.assertIn("ModelForm ausente", str(context.exception))
