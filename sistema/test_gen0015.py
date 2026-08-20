from django.test import TestCase

from .compiler import SpecificationCompiler
from .test_gen0013_0014 import build_spec


class Gen0015AuthenticationPermissionTests(TestCase):
    def _compiled(self):
        return SpecificationCompiler(build_spec()).compile()

    def test_generated_views_require_login_and_model_permissions(self):
        views = next(i.content for i in self._compiled() if i.path == "cadastro/views.py")
        self.assertIn("LoginRequiredMixin", views)
        self.assertIn("PermissionRequiredMixin", views)
        self.assertIn('permission_required = "cadastro.view_pessoa"', views)
        self.assertIn('permission_required = "cadastro.add_pessoa"', views)
        self.assertIn('permission_required = "cadastro.change_pessoa"', views)
        self.assertIn('permission_required = "cadastro.delete_pessoa"', views)

    def test_generated_list_exposes_permission_aware_actions(self):
        views = next(i.content for i in self._compiled() if i.path == "cadastro/views.py")
        listing = next(i.content for i in self._compiled() if i.path.endswith("pessoa_list.html"))
        self.assertIn('has_perm("cadastro.add_pessoa")', views)
        self.assertIn('has_perm("cadastro.change_pessoa")', views)
        self.assertIn('has_perm("cadastro.delete_pessoa")', views)
        self.assertIn("pode_criar", listing)
        self.assertIn("pode_editar", listing)
        self.assertIn("pode_excluir", listing)

    def test_generated_base_hides_navigation_without_view_permission(self):
        base = next(i.content for i in self._compiled() if i.path == "templates/base.html")
        self.assertIn("perms.cadastro.view_pessoa", base)
        self.assertIn("request.resolver_match.url_name", base)

    def test_authentication_contract_remains_in_generated_base(self):
        base = next(i.content for i in self._compiled() if i.path == "templates/base.html")
        self.assertIn("user.is_authenticated", base)
        self.assertIn("{% url 'login' %}", base)
        self.assertIn("{% url 'logout' %}", base)

    def test_generated_settings_define_authentication_contract(self):
        settings = next(i.content for i in self._compiled() if i.path.endswith("/settings.py"))
        self.assertIn('"django.contrib.auth.middleware.AuthenticationMiddleware"', settings)
        self.assertIn('"django.contrib.auth.backends.ModelBackend"', settings)
        self.assertIn('LOGIN_URL = "/accounts/login/"', settings)
        self.assertIn('LOGIN_REDIRECT_URL = "/"', settings)
        self.assertIn('LOGOUT_REDIRECT_URL = "/accounts/login/"', settings)

    def test_root_urls_expose_django_authentication_and_protect_dashboard(self):
        urls = next(i.content for i in self._compiled() if i.path.endswith("/urls.py"))
        self.assertIn('include("django.contrib.auth.urls")', urls)
        self.assertIn("login_required", urls)
        self.assertIn('template_name="index.html"', urls)
