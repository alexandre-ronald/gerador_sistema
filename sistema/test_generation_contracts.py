from types import SimpleNamespace

from django.test import SimpleTestCase
from django.template.loader import render_to_string


class GeneratedTemplateContractTests(SimpleTestCase):
    def test_form_template_preserves_runtime_form_tags(self):
        content = render_to_string(
            "gerador/snippets/html_form.txt",
            {
                "app_name": "gestao_de_pessoas",
                "entidade": SimpleNamespace(nome="Funcionário", codigo_nome="funcionario"),
            },
        )
        self.assertIn("{{ form.as_div }}", content)
        self.assertIn("{% csrf_token %}", content)

    def test_index_template_uses_python_safe_namespace(self):
        content = render_to_string(
            "gerador/snippets/index_html.txt",
            {"modulos": [], "sistema": SimpleNamespace(nome="Teste", modulos=[])},
        )
        self.assertIn("{{ modulo.app_name }}:{{ entidade.codigo_nome }}_list", content)
        self.assertNotIn("{{ modulo.nome|lower }}:{{ entidade.nome|lower }}_list", content)

    def test_base_template_uses_python_safe_namespace(self):
        content = render_to_string(
            "gerador/snippets/base_html.txt",
            {"modulos": [], "sistema": SimpleNamespace(nome="Teste", tipo_menu="lateral")},
        )
        self.assertIn("{{ modulo.app_name }}:{{ entidade.codigo_nome }}_list", content)
        self.assertIn("request.resolver_match.app_name", content)
        self.assertIn("perms.", content)

    def test_form_snippet_is_not_evaluated_by_generator(self):
        content = render_to_string(
            "gerador/snippets/html_form.txt",
            {
                "app_name": "eleicao",
                "entidade": SimpleNamespace(nome="Funcionário", codigo_nome="funcionario"),
            },
        )
        self.assertIn("{{ form.as_div }}", content)
        self.assertNotIn("Salvar Registro</button>\n", content.replace("{{ form.as_div }}", ""))
