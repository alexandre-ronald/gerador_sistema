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
        self.assertIn("forms.CheckboxInput", content)
        self.assertNotIn("class BootstrapModelForm", content)

    def test_boolean_form_controls_use_stable_switch_layout(self):
        content = self._source("gerador/snippets/html_form.txt")
        self.assertIn("app-boolean-field", content)
        self.assertIn(".app-boolean-field .form-check-input", content)
        self.assertIn("margin:0!important", content)
        self.assertIn("float:none!important", content)
        self.assertIn('class="form-check form-switch app-boolean-field border"', content)
        self.assertNotIn('form-switch p-3 rounded-3', content)
        self.assertNotIn('<span>{% templatetag openvariable %} field {% templatetag closevariable %}</span>', content)

    def test_navigation_is_centralized_and_python_safe(self):
        base = self._source("gerador/snippets/base_html.txt"); index = self._source("gerador/snippets/index_html.txt"); navigation = self._source("gerador/snippets/navigation_context.txt")
        self.assertIn("navigation_modules", base); self.assertIn("navigation_modules", index); self.assertIn("url item.url_name", base); self.assertIn("url item.url_name", index)
        self.assertIn('{% templatetag openvariable %} item.permission {% templatetag closevariable %}', base); self.assertIn("item.is_active", base); self.assertNotIn("request.resolver_match.app_name == item.app_name", base)
        self.assertIn("{% templatetag openblock %} for modulo in navigation_modules {% templatetag closeblock %}", base); self.assertIn("{% templatetag openblock %} for item in modulo.items {% templatetag closeblock %}", base)
        self.assertIn("NAVIGATION_MODULES", navigation); self.assertIn("user.has_perm", navigation); self.assertIn("{{ modulo.app_name }}:{{ entidade.codigo_nome }}_list", navigation)
        self.assertIn('"active_url_names": [', navigation); self.assertIn('"{{ entidade.codigo_nome }}_create"', navigation); self.assertIn('"{{ entidade.codigo_nome }}_update"', navigation); self.assertIn('"{{ entidade.codigo_nome }}_detail"', navigation); self.assertIn('"is_active":', navigation); self.assertIn("current_url_name in active_names", navigation)
        self.assertNotIn("gestão de pessoas:funcionário_list", base.lower()); self.assertNotIn("gestão de pessoas:funcionário_list", index.lower())

    def test_generated_ui_uses_modern_feedback_without_browser_dialogs(self):
        base = self._source("gerador/snippets/base_html.txt"); form = self._source("gerador/snippets/html_form.txt"); login = self._source("gerador/snippets/login_html.txt"); index = self._source("gerador/snippets/index_html.txt"); detail = self._source("gerador/snippets/html_detail.txt")
        self.assertIn("app-toast-stack", base); self.assertIn("data-app-toast", base); self.assertIn("app-page-heading", index); self.assertIn("app-page-heading", form); self.assertIn("app-feedback-danger", form); self.assertIn("auth-feedback", login)
        self.assertIn("workflowConfirmModal", detail)
        for content in (base, form, login, detail):
            self.assertNotIn("alert alert-", content); self.assertNotIn("alert(", content); self.assertNotIn("confirm(", content)

    def test_dashboard_runtime_parses_json_instead_of_executing_json_literals_as_python(self):
        content = self._source("gerador/snippets/dashboard_data_views.txt")
        self.assertIn("import json", content)
        self.assertIn('widgets = json.loads(r"""{{ dashboard_json|safe }}""")', content)
        self.assertNotIn("widgets={{ dashboard_json|safe }}", content)

    def test_boolean_values_have_explicit_runtime_presentation(self):
        listing = self._source("gerador/snippets/html_list.txt"); detail = self._source("gerador/snippets/html_detail.txt")
        self.assertIn("coluna.tipo == 'BooleanField'", listing); self.assertIn("campo.tipo == 'BooleanField'", listing); self.assertIn("coluna.tipo == 'BooleanField'", detail)
        self.assertIn("bi-check-circle-fill", listing); self.assertIn("Sim", listing); self.assertIn("Não", listing)

    def test_settings_registers_the_single_navigation_context_processor(self):
        content = self._source("gerador/snippets/settings.txt")
        self.assertIn("{{ nome_projeto }}.context_processors.navigation", content)

    def test_views_keep_permission_enforcement(self):
        content = self._source("gerador/snippets/views.txt")
        self.assertIn("PermissionRequiredMixin", content); self.assertIn("permission_required = '{{ app_name }}.view_{{ entidade.codigo_nome }}'", content); self.assertIn("permission_required = '{{ app_name }}.add_{{ entidade.codigo_nome }}'", content)

    def test_generator_uses_python_safe_identifier_pipeline(self):
        from sistema.services import GeradorService
        self.assertEqual(GeradorService._python_identifier("Gestão de Pessoas"), "gestao_de_pessoas"); self.assertEqual(GeradorService._class_name("Funcionário"), "Funcionario"); self.assertEqual(GeradorService._python_identifier("Número do Documento"), "numero_do_documento")
