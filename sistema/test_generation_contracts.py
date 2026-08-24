from django.test import SimpleTestCase
from django.template.loader import get_template


class GeneratedTemplateContractTests(SimpleTestCase):
    @staticmethod
    def _source(name):
        return get_template(name).template.source

    def test_form_template_preserves_runtime_form_tags(self):
        content = self._source("gerador/snippets/html_form.txt")
        self.assertIn("{% templatetag openblock %} csrf_token {% templatetag closeblock %}", content)
        self.assertIn("{% templatetag openblock %} for field in form {% templatetag closeblock %}", content)
        self.assertIn("{% templatetag openvariable %} field {% templatetag closevariable %}", content)

    def test_index_template_emits_explicit_python_safe_namespace(self):
        content = self._source("gerador/snippets/index_html.txt")
        self.assertIn("{% templatetag openblock %} url '{{ modulo.app_name }}:{{ entidade.codigo_nome }}_list' {% templatetag closeblock %}", content)
        self.assertIn("{% for entidade in modulo.entidades_geracao %}", content)
        self.assertNotIn("gestão de pessoas:funcionário_list", content.lower())
        self.assertNotIn("{{ modulo.nome|lower }}:{{ entidade.nome|lower }}_list", content)

    def test_base_template_emits_explicit_python_safe_namespace(self):
        content = self._source("gerador/snippets/base_html.txt")
        self.assertIn("{% templatetag openblock %} url '{{ modulo.app_name }}:{{ entidade.codigo_nome }}_list' {% templatetag closeblock %}", content)
        self.assertIn("request.resolver_match.app_name", content)
        self.assertIn("{% for modulo in modulos %}", content)
        self.assertIn("{% for entidade in modulo.entidades_geracao %}", content)
        self.assertNotIn("{{ modulo.nome|lower }}:{{ entidade.nome|lower }}_list", content)

    def test_base_template_preserves_navigation_contract_for_superior_menu(self):
        content = self._source("gerador/snippets/base_html.txt")
        self.assertIn("{% if sistema.tipo_menu == 'superior' %}", content)
        self.assertIn("{% for entidade in modulo.entidades_geracao %}", content)
        self.assertIn("request.resolver_match.app_name", content)

    def test_base_template_keeps_app_navigation_without_crud_entities(self):
        content = self._source("gerador/snippets/base_html.txt")
        self.assertIn("{% for modulo in modulos %}", content)
        self.assertIn("{{ modulo.nome }}", content)
        self.assertIn("{{ modulo.app_name }}", content)
