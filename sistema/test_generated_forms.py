from types import SimpleNamespace

from django.test import SimpleTestCase
from django.template.loader import render_to_string


class GeneratedFormsSnippetTests(SimpleTestCase):
    """Regression tests for the generated forms.py contract."""

    def _render_forms(self):
        entidade = SimpleNamespace(classe_nome="FuncionRio")
        return render_to_string(
            "gerador/snippets/forms_v2.txt",
            {"entidades": [entidade]},
        )

    def test_generated_forms_imports_model_classes(self):
        content = self._render_forms()
        self.assertIn("from .models import FuncionRio", content)
        self.assertIn("model = FuncionRio", content)

    def test_generated_form_is_self_contained(self):
        content = self._render_forms()
        self.assertNotIn("model = FuncionRio\n", content.replace(
            "from .models import FuncionRio\n", ""
        ))
