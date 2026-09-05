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
        self.assertIn("fields = [", content); self.assertIn('{{ campo.codigo_nome }}', content); self.assertIn("class {{ entidade.classe_nome }}Form(forms.ModelForm):", content); self.assertIn("configurar_widgets_bootstrap(self)", content); self.assertIn("forms.CheckboxInput", content); self.assertNotIn("class BootstrapModelForm", content)

    def test_boolean_form_controls_use_stable_switch_layout(self):
        content = self._source("gerador/snippets/html_form.txt")
        self.assertIn("app-boolean-field", content); self.assertIn(".app-boolean-field .form-check-input", content); self.assertIn("margin:0!important", content); self.assertIn("float:none!important", content); self.assertIn('class="form-check form-switch app-boolean-field border"', content); self.assertNotIn('form-switch p-3 rounded-3', content)

    def test_navigation_is_centralized_and_python_safe(self):
        base = self._source("gerador/snippets/base_html.txt"); index = self._source("gerador/snippets/index_html.txt"); navigation = self._source("gerador/snippets/navigation_context.txt")
        self.assertIn("navigation_modules", base); self.assertIn("navigation_modules", index); self.assertIn("url item.url_name", base); self.assertIn("url item.url_name", index); self.assertIn('{% templatetag openvariable %} item.permission {% templatetag closevariable %}', base); self.assertIn("item.is_active", base); self.assertNotIn("request.resolver_match.app_name == item.app_name", base)
        self.assertIn("NAVIGATION_MODULES", navigation); self.assertIn("user.has_perm", navigation); self.assertIn("{{ modulo.app_name }}:{{ entidade.codigo_nome }}_list", navigation); self.assertIn('"active_url_names": [', navigation); self.assertIn("current_url_name in active_names", navigation)

    def test_global_navigation_exposes_context_and_compact_sidebar(self):
        base = self._source("gerador/snippets/base_html.txt"); navigation = self._source("gerador/snippets/navigation_context.txt")
        self.assertIn("navigation_current", navigation); self.assertIn("_current_navigation_context", navigation); self.assertIn("sidebar-collapse", base); self.assertIn("sidebar-collapsed", base); self.assertIn("localStorage.setItem('sidebar-collapsed'", base); self.assertIn("navigation_current.module_label", base); self.assertIn("navigation_current.item_label", base); self.assertIn("url 'dashboard'", base); self.assertIn("app-user-menu", base); self.assertIn("Sair do sistema", base); self.assertIn("aria-controls=\"app-sidebar\"", base)

    def test_transaction_navigation_uses_meaningful_icon_when_collapsed(self):
        base = self._source("gerador/snippets/base_html.txt")
        self.assertIn("bi-table", base)
        self.assertIn("bi-file-earmark-bar-graph", base)
        self.assertIn("item.is_report", base)
        self.assertNotIn('bi bi-circle-fill', base)

    def test_generated_runtime_includes_profile_and_staff_user_management(self):
        base = self._source("gerador/snippets/base_html.txt"); urls = self._source("gerador/snippets/urls_root_v2.txt"); navigation = self._source("gerador/snippets/navigation_context.txt"); user_form = self._source("gerador/snippets/user_form_html.txt"); user_list = self._source("gerador/snippets/user_list_html.txt")
        self.assertIn("url 'profile'", base); self.assertIn("url 'user_list'", base); self.assertIn("Meu perfil", base); self.assertIn("user.is_staff", base)
        self.assertIn("profile_view", urls); self.assertIn("password_change_view", urls); self.assertIn("user_list_view", urls); self.assertIn("user_create_view", urls); self.assertIn("user_update_view", urls); self.assertIn("UserCreationForm", urls); self.assertIn("get_object_or_404", urls); self.assertIn("_staff_required", urls)
        self.assertIn("Novo usuário", user_list); self.assertIn("Perfis de acesso", user_form); self.assertIn('current_url_name in {"profile", "password_change"}', navigation); self.assertIn('current_url_name in {"user_list", "user_create", "user_update"}', navigation)

    def test_generated_rbac_profiles_sync_django_groups_and_permissions(self):
        urls = self._source("gerador/snippets/urls_root_v2.txt"); base = self._source("gerador/snippets/base_html.txt"); user_form = self._source("gerador/snippets/user_form_html.txt"); user_list = self._source("gerador/snippets/user_list_html.txt")
        self.assertIn("rbac_system_runtime_config", urls)
        self.assertIn("RBAC_ROLE_GROUPS", urls)
        self.assertIn("Group.objects.get_or_create", urls)
        self.assertIn("Permission.objects.filter", urls)
        self.assertIn("group.permissions.set", urls)
        self.assertIn("_save_user_role_groups", urls)
        self.assertIn("request.POST.getlist('groups')", urls)
        self.assertIn("name=\"groups\"", user_form)
        self.assertIn("role_groups", user_form)
        self.assertIn("role_mode", user_list)
        self.assertIn("url 'role_list'", base)
        self.assertIn("Perfis de acesso", base)

    def test_base_is_layout_only_and_account_pages_extend_it(self):
        base = self._source("gerador/snippets/base_html.txt")
        profile = self._source("gerador/snippets/profile_html.txt")
        password = self._source("gerador/snippets/password_change_html.txt")
        user_form = self._source("gerador/snippets/user_form_html.txt")
        user_list = self._source("gerador/snippets/user_list_html.txt")
        self.assertIn("{% templatetag openblock %} block content {% templatetag closeblock %}", base)
        self.assertNotIn("request.resolver_match.url_name == 'profile'", base)
        for content in (profile, password, user_form, user_list):
            self.assertIn('{% templatetag openblock %} extends "base.html" {% templatetag closeblock %}', content)

    def test_generated_ui_uses_modern_feedback_without_browser_dialogs(self):
        base = self._source("gerador/snippets/base_html.txt"); form = self._source("gerador/snippets/html_form.txt"); login = self._source("gerador/snippets/login_html.txt"); index = self._source("gerador/snippets/index_html.txt"); detail = self._source("gerador/snippets/html_detail.txt"); dashboard = self._source("gerador/snippets/dashboard_html.txt"); home = self._source("gerador/snippets/home_html.txt")
        self.assertIn("app-toast-stack", base); self.assertIn("data-app-toast", base); self.assertIn("workspace-hero", index); self.assertIn("app-page-heading", form); self.assertIn("app-feedback-danger", form); self.assertIn("auth-feedback", login); self.assertIn("workflowConfirmModal", detail); self.assertIn("dashboard-status", dashboard); self.assertIn("dashboard-refresh", dashboard); self.assertIn("dashboard-skeleton", dashboard)
        for content in (base, form, login, detail, index, dashboard, home): self.assertNotIn("alert alert-", content); self.assertNotIn("alert(", content); self.assertNotIn("confirm(", content)

    def test_dashboard_uses_named_runtime_routes(self):
        dashboard = self._source("gerador/snippets/dashboard_html.txt")
        self.assertIn("{% templatetag openblock %} url 'index' {% templatetag closeblock %}", dashboard); self.assertIn('{% templatetag openblock %} url "dashboard_data" {% templatetag closeblock %}', dashboard); self.assertNotIn('href="/" class="btn btn-primary"', dashboard)

    def test_dashboard_runtime_parses_json_instead_of_executing_json_literals_as_python(self):
        content = self._source("gerador/snippets/dashboard_data_views.txt")
        self.assertIn("import json", content); self.assertIn('widgets = json.loads(r"""{{ dashboard_json|safe }}""")', content); self.assertNotIn("widgets={{ dashboard_json|safe }}", content)

    def test_boolean_values_have_explicit_runtime_presentation(self):
        listing = self._source("gerador/snippets/html_list.txt"); detail = self._source("gerador/snippets/html_detail.txt")
        self.assertIn("coluna.tipo == 'BooleanField'", listing); self.assertIn("campo.tipo == 'BooleanField'", listing); self.assertIn("coluna.tipo == 'BooleanField'", detail); self.assertIn("bi-check-circle-fill", listing); self.assertIn("Sim", listing); self.assertIn("Não", listing)

    def test_related_models_use_descriptive_labels_in_forms_and_filters(self):
        models = self._source("gerador/snippets/models.txt"); listing = self._source("gerador/snippets/html_list.txt"); navigation = self._source("gerador/snippets/navigation_context.txt")
        self.assertIn('campo.tipo == "CharField"', models); self.assertIn('campo.tipo == "TextField"', models); self.assertIn('campo.tipo != "BooleanField"', models); self.assertIn("return str(self.pk)", models); self.assertIn("relation_filter_choices", navigation); self.assertIn("related_model._default_manager.all()[:500]", navigation); self.assertIn('"label": str(obj)', navigation); self.assertIn("filtro.type == 'relation'", listing); self.assertIn('relation.field == \'{{ filtro.codigo_nome }}\'', listing); self.assertIn("option.label", listing); self.assertNotIn('placeholder="ID do registro relacionado"', listing)

    def test_settings_registers_the_single_navigation_context_processor(self):
        content = self._source("gerador/snippets/settings.txt"); self.assertIn("{{ nome_projeto }}.context_processors.navigation", content)

    def test_views_keep_permission_enforcement(self):
        content = self._source("gerador/snippets/views.txt"); self.assertIn("PermissionRequiredMixin", content); self.assertIn("permission_required = '{{ app_name }}.view_{{ entidade.codigo_nome }}'", content); self.assertIn("permission_required = '{{ app_name }}.add_{{ entidade.codigo_nome }}'", content)

    def test_generator_uses_python_safe_identifier_pipeline(self):
        from sistema.services import GeradorService
        self.assertEqual(GeradorService._python_identifier("Gestão de Pessoas"), "gestao_de_pessoas"); self.assertEqual(GeradorService._class_name("Funcionário"), "Funcionario"); self.assertEqual(GeradorService._python_identifier("Número do Documento"), "numero_do_documento")
