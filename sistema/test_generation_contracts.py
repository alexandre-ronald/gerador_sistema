from django.test import SimpleTestCase
from django.template.loader import get_template


class GeneratedTemplateContractTests(SimpleTestCase):
    @staticmethod
    def _source(name):
        return get_template(name).template.source

    def test_form_template_renders_runtime_fields(self):
        content = self._source("gerador/snippets/html_form.txt")
        self.assertIn("{% templatetag openblock %} csrf_token {% templatetag closeblock %}", content)
        self.assertIn("{% templatetag openblock %} for field in form.visible_fields {% templatetag closeblock %}", content)
        self.assertIn("{% templatetag openvariable %} field {% templatetag closevariable %}", content)
        self.assertIn("{% templatetag openblock %} for hidden in form.hidden_fields {% templatetag closeblock %}", content)

    def test_forms_template_is_self_contained_and_explicit(self):
        content = self._source("gerador/snippets/forms_v2.txt")
        self.assertIn("fields = [", content)
        self.assertIn('{{ campo.codigo_nome }}', content)
        self.assertIn("class {{ entidade.classe_nome }}Form(forms.ModelForm):", content)
        self.assertIn("configurar_widgets_bootstrap(self)", content)
        self.assertNotIn("class BootstrapModelForm", content)

    def test_navigation_is_centralized_and_python_safe(self):
        base = self._source("gerador/snippets/base_html.txt")
        index = self._source("gerador/snippets/index_html.txt")
        navigation = self._source("gerador/snippets/navigation_context.txt")
        self.assertIn("navigation_modules", base)
        self.assertIn("navigation_modules", index)
        self.assertIn("url item.url_name", base)
        self.assertIn("url item.url_name", index)
        self.assertIn('{% templatetag openvariable %} item.permission {% templatetag closevariable %}', base)
        self.assertIn("item.is_active", base)
        self.assertNotIn("request.resolver_match.app_name == item.app_name", base)
        self.assertIn("{% templatetag openblock %} for modulo in navigation_modules {% templatetag closeblock %}", base)
        self.assertIn("{% templatetag openblock %} for item in modulo.items {% templatetag closeblock %}", base)
        self.assertIn("NAVIGATION_MODULES", navigation)
        self.assertIn("user.has_perm", navigation)
        self.assertIn("{{ modulo.app_name }}:{{ entidade.codigo_nome }}_list", navigation)
        self.assertIn('"active_url_names": [', navigation)
        self.assertIn('"{{ entidade.codigo_nome }}_create"', navigation)
        self.assertIn('"{{ entidade.codigo_nome }}_update"', navigation)
        self.assertIn('"{{ entidade.codigo_nome }}_detail"', navigation)
        self.assertIn('"is_active":', navigation)
        self.assertIn("current_url_name in active_names", navigation)
        self.assertNotIn("gestão de pessoas:funcionário_list", base.lower())
        self.assertNotIn("gestão de pessoas:funcionário_list", index.lower())

    def test_generated_ui_uses_modern_feedback_without_alert_components(self):
        base = self._source("gerador/snippets/base_html.txt")
        form = self._source("gerador/snippets/html_form.txt")
        login = self._source("gerador/snippets/login_html.txt")
        index = self._source("gerador/snippets/index_html.txt")

        self.assertIn("app-toast-stack", base)
        self.assertIn("data-app-toast", base)
        self.assertIn("app-page-heading", index)
        self.assertIn("app-page-heading", form)
        self.assertIn("app-feedback-danger", form)
        self.assertIn("auth-feedback", login)
        self.assertNotIn("alert alert-", base)
        self.assertNotIn("alert alert-", form)
        self.assertNotIn("alert alert-", login)
        self.assertNotIn("alert(", base)
        self.assertNotIn("confirm(", base)
        self.assertNotIn("alert(", login)
        self.assertNotIn("confirm(", login)

    def test_settings_registers_the_single_navigation_context_processor(self):
        content = self._source("gerador/snippets/settings.txt")
        self.assertIn("{{ nome_projeto }}.context_processors.navigation", content)

    def test_views_keep_permission_enforcement(self):
        content = self._source("gerador/snippets/views.txt")
        self.assertIn("PermissionRequiredMixin", content)
        self.assertIn("permission_required = '{{ app_name }}.view_{{ entidade.codigo_nome }}'", content)
        self.assertIn("permission_required = '{{ app_name }}.add_{{ entidade.codigo_nome }}'", content)

    def test_generator_uses_python_safe_identifier_pipeline(self):
        from sistema.services import GeradorService
        self.assertEqual(GeradorService._python_identifier("Gestão de Pessoas"), "gestao_de_pessoas")
        self.assertEqual(GeradorService._class_name("Funcionário"), "Funcionario")
        self.assertEqual(GeradorService._python_identifier("Número do Documento"), "numero_do_documento")
