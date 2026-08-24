from django.template import Template
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
        self.assertIn("{% templatetag openvariable %} form.as_div {% templatetag closevariable %}", content)
        self.assertIn("url_name=app_name|add:\":\"|add:entidade.codigo_nome|add:\"_list\"", content)

    def test_index_template_uses_python_safe_namespace(self):
        content = self._source("gerador/snippets/index_html.txt")
        self.assertIn("modulo.app_name|add:\":\"|add:entidade.codigo_nome|add:\"_list\"", content)
        self.assertIn("{% templatetag openblock %} url url_name {% templatetag closeblock %}", content)
        self.assertIn("{% for entidade in modulo.entidades_geracao %}", content)
        self.assertNotIn("gestão de pessoas:funcionário_list", content.lower())
        self.assertNotIn("{{ modulo.nome|lower }}:{{ entidade.nome|lower }}_list", content)

    def test_base_template_uses_python_safe_namespace(self):
        content = self._source("gerador/snippets/base_html.txt")
        self.assertIn("modulo.app_name|add:\".view_\"|add:entidade.codigo_nome", content)
        self.assertIn("modulo.app_name|add:\":\"|add:entidade.codigo_nome|add:\"_list\"", content)
        self.assertIn("{% templatetag openblock %} url url_name {% templatetag closeblock %}", content)
        self.assertIn("request.resolver_match.app_name", content)
        self.assertIn("perms.", content)
        self.assertNotIn("{{ modulo.app_name }}:{{ entidade.codigo_nome }}_list", content)
        self.assertNotIn("{{ modulo.nome|lower }}:{{ entidade.nome|lower }}_list", content)

    def test_base_template_preserves_navigation_contract_for_superior_menu(self):
        content = self._source("gerador/snippets/base_html.txt")
        self.assertIn("{% if sistema.tipo_menu == 'superior' %}", content)
        self.assertIn("{% for entidade in modulo.entidades_geracao %}", content)
        self.assertIn("request.resolver_match.app_name", content)
        self.assertIn("perms.", content)

    def test_base_template_keeps_app_navigation_without_crud_entities(self):
        content = self._source("gerador/snippets/base_html.txt")
        self.assertIn("{% for modulo in modulos %}", content)
        self.assertIn("{{ modulo.nome }}", content)
        self.assertIn("{{ modulo.app_name }}", content)
        self.assertIn("request.resolver_match.app_name", content)
