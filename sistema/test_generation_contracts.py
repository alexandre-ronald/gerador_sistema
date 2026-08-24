from types import SimpleNamespace

from django.test import SimpleTestCase
from django.template.loader import render_to_string


class _RelatedManagerStub:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return self._items


class GeneratedTemplateContractTests(SimpleTestCase):
    def _module_context(self, tipo_menu="lateral", gerar_crud_views=True):
        entidade = SimpleNamespace(
            nome="Funcionário",
            codigo_nome="funcionario",
            gerar_crud_views=gerar_crud_views,
        )
        modulo = SimpleNamespace(
            nome="Gestão de Pessoas",
            app_name="gestao_de_pessoas",
            entidades=_RelatedManagerStub([entidade]),
        )
        sistema = SimpleNamespace(
            nome="Teste",
            tipo_menu=tipo_menu,
            modulos=_RelatedManagerStub([modulo]),
        )
        return modulo, entidade, sistema

    def _render_base(self, sistema):
        return render_to_string(
            "gerador/snippets/base_html.txt",
            {"modulos": list(sistema.modulos.all()), "sistema": sistema},
        )

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
        modulo, entidade, sistema = self._module_context()
        content = render_to_string(
            "gerador/snippets/index_html.txt",
            {"modulos": [modulo], "sistema": sistema},
        )
        self.assertIn("gestao_de_pessoas:funcionario_list", content)
        self.assertNotIn("gestão de pessoas:funcionário_list", content)
        self.assertNotIn("{{ modulo.nome|lower }}:{{ entidade.nome|lower }}_list", content)

    def test_base_template_uses_python_safe_namespace(self):
        _, _, sistema = self._module_context()
        content = self._render_base(sistema)
        self.assertIn("gestao_de_pessoas:funcionario_list", content)
        self.assertIn("request.resolver_match.app_name", content)
        self.assertIn("perms.", content)

    def test_base_template_preserves_navigation_contract_for_superior_menu(self):
        _, _, sistema = self._module_context(tipo_menu="superior")
        content = self._render_base(sistema)
        self.assertIn("gestao_de_pessoas:funcionario_list", content)
        self.assertIn("request.resolver_match.app_name", content)
        self.assertIn("perms.", content)

    def test_base_template_keeps_app_navigation_without_crud_entities(self):
        _, _, sistema = self._module_context(gerar_crud_views=False)
        content = self._render_base(sistema)
        self.assertIn("request.resolver_match.app_name", content)
        self.assertIn("gestao_de_pessoas", content)
        self.assertIn("Gestão de Pessoas", content)

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
