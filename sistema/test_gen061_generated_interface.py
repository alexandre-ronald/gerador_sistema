from types import SimpleNamespace

from django.test import SimpleTestCase
from django.template.loader import render_to_string


class GeneratedInterfaceDesignerTests(SimpleTestCase):
    def _render_base(
        self,
        *,
        menu="lateral",
        modo="automatico",
        densidade="confortavel",
        breadcrumb=True,
        busca=True,
        menu_usuario=True,
    ):
        sistema = SimpleNamespace(
            nome="Gestão de Contratos",
            interface_nome="Gestão de Contratos",
            tipo_menu=menu,
            interface_modo=modo,
            interface_densidade=densidade,
            interface_cor_primaria="#123456",
            interface_cor_destaque="#abcdef",
            interface_breadcrumb=breadcrumb,
            interface_busca=busca,
            interface_menu_usuario=menu_usuario,
        )

        return render_to_string(
            "gerador/snippets/base_html.txt",
            {"sistema": sistema},
        )

    def test_interface_visual_configuration_is_rendered(self):
        content = self._render_base(
            menu="superior",
            modo="escuro",
            densidade="compacta",
        )

        self.assertIn('data-bs-theme="dark"', content)
        self.assertIn("#123456", content)
        self.assertIn("#abcdef", content)
        self.assertIn("Gestão de Contratos", content)
        self.assertIn("Navegação de módulos", content)

    def test_optional_elements_are_rendered_when_enabled(self):
        content = self._render_base(
            breadcrumb=True,
            busca=True,
            menu_usuario=True,
        )

        self.assertIn('aria-label="breadcrumb"', content)
        self.assertIn('id="app-navigation-search"', content)
        self.assertIn('class="dropdown app-user-menu"', content)

    def test_optional_elements_are_not_rendered_when_disabled(self):
        content = self._render_base(
            breadcrumb=False,
            busca=False,
            menu_usuario=False,
        )

        self.assertNotIn('aria-label="breadcrumb"', content)
        self.assertNotIn('id="app-navigation-search"', content)
        self.assertNotIn('class="dropdown app-user-menu"', content)

    def test_logout_contract_survives_without_user_menu(self):
        content = self._render_base(menu_usuario=False)

        self.assertIn("url 'logout'", content)
        self.assertIn("csrf_token", content)
        self.assertIn("Sair do sistema", content)

    def test_search_does_not_depend_on_missing_search_route(self):
        content = self._render_base(busca=True)

        self.assertNotIn("url 'search'", content)
        self.assertIn("app-navigation-search", content)
        self.assertIn("Buscar no menu", content)

    def test_automatic_theme_contract_is_preserved(self):
        content = self._render_base(modo="automatico")

        self.assertIn("prefers-color-scheme: dark", content)
        self.assertIn('data-interface-mode="automatico"', content)
