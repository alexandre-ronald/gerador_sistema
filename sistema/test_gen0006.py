from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase

from .compiler import SpecificationCompiler
from .models import Campo, Entidade, Modulo, Sistema
from .specification import build_specification
from django.contrib.auth import get_user_model

User = get_user_model()


class Gen0006FormsRichTests(TestCase):
    def test_generated_form_contains_semantic_widget_rules(self):
        user = User.objects.create_user(username="gen0006", password="secret123")
        sistema = Sistema.objects.create(usuario=user, nome="Sistema Forms GEN-0006")
        modulo = Modulo.objects.create(sistema=sistema, nome="Cadastro")
        entidade = Entidade.objects.create(
            modulo=modulo,
            nome="Pessoa",
            gerar_crud_views=True,
        )
        Campo.objects.create(entidade=entidade, nome="Nome", tipo="CharField", max_length=100)
        Campo.objects.create(entidade=entidade, nome="Ativo", tipo="BooleanField")
        Campo.objects.create(entidade=entidade, nome="Nascimento", tipo="DateField")
        Campo.objects.create(entidade=entidade, nome="Hora Cadastro", tipo="TimeField")
        Campo.objects.create(entidade=entidade, nome="Arquivo", tipo="FileField", upload_to="uploads/")

        spec = build_specification(sistema)
        with TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            SpecificationCompiler(spec).write(root)
            content = (root / "cadastro/forms.py").read_text(encoding="utf-8")

        self.assertIn('"class": "form-check-input"', content)
        self.assertIn('"class": "form-select"', content)
        self.assertIn('widget.input_type = "date"', content)
        self.assertIn('widget.input_type = "time"', content)
        self.assertIn('"class": "form-control"', content)

    def test_generated_form_preserves_model_form_contract(self):
        user = User.objects.create_user(username="gen0006contract", password="secret123")
        sistema = Sistema.objects.create(usuario=user, nome="Sistema Contract GEN-0006")
        modulo = Modulo.objects.create(sistema=sistema, nome="Cadastro")
        entidade = Entidade.objects.create(modulo=modulo, nome="Pessoa")
        Campo.objects.create(entidade=entidade, nome="Nome", tipo="CharField", max_length=100)

        spec = build_specification(sistema)
        with TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            SpecificationCompiler(spec).write(root)
            content = (root / "cadastro/forms.py").read_text(encoding="utf-8")

        self.assertIn("class PessoaForm(forms.ModelForm):", content)
        self.assertIn("model = Pessoa", content)
        self.assertIn('fields = "__all__"', content)
