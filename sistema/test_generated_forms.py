from types import SimpleNamespace

from django.test import SimpleTestCase
from django.template.loader import render_to_string


class GeneratedFormsSnippetTests(SimpleTestCase):
    """Regression tests for the generated forms.py contract."""

    def _render_forms(self):
        entidade = SimpleNamespace(classe_nome="Funcionario")
        return render_to_string(
            "gerador/snippets/forms_v2.txt",
            {"entidades": [entidade]},
        )

    def test_generated_forms_imports_model_classes(self):
        content = self._render_forms()
        self.assertIn("from .models import Funcionario", content)
        self.assertIn("model = Funcionario", content)

    def test_generated_form_is_self_contained(self):
        content = self._render_forms()
        import_line = "from .models import Funcionario\n"
        model_line = "model = Funcionario\n"
        self.assertNotIn("FuncionRio", content)
        self.assertLess(content.index(import_line), content.index(model_line))
        self.assertIn("class FuncionarioForm(forms.ModelForm):", content)
