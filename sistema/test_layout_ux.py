from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Sistema


class LayoutUXDeletionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="layout-owner",
            password="senha-forte",
        )
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema Exclusão Segura",
        )
        self.client.force_login(self.user)

    def test_lista_uses_modal_instead_of_browser_confirm(self):
        response = self.client.get(reverse("sistema:lista"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="deleteSystemModal"')
        self.assertContains(response, "Excluir definitivamente")
        self.assertContains(response, "Esta operação não pode ser desfeita")
        self.assertNotContains(response, "return confirm(")

    def test_delete_rejects_get(self):
        response = self.client.get(
            reverse("sistema:excluir_sistema", args=[self.sistema.pk])
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Sistema.objects.filter(pk=self.sistema.pk).exists())

    def test_delete_accepts_post_for_owner(self):
        response = self.client.post(
            reverse("sistema:excluir_sistema", args=[self.sistema.pk])
        )

        self.assertRedirects(response, reverse("sistema:lista"))
        self.assertFalse(Sistema.objects.filter(pk=self.sistema.pk).exists())

    def test_delete_cannot_remove_another_users_system(self):
        other = get_user_model().objects.create_user(
            username="layout-other",
            password="senha-forte",
        )
        foreign_system = Sistema.objects.create(
            usuario=other,
            nome="Sistema de Outro Usuário",
        )

        response = self.client.post(
            reverse("sistema:excluir_sistema", args=[foreign_system.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Sistema.objects.filter(pk=foreign_system.pk).exists())


class LayoutUXNavigationContractTests(TestCase):
    TOOL_TEMPLATES = (
        "sistema/templates/sistema/form_designer.html",
        "sistema/templates/sistema/crud_designer.html",
        "sistema/templates/sistema/business_rules_designer.html",
        "sistema/templates/sistema/workflow_designer.html",
        "sistema/templates/sistema/permission_designer.html",
        "sistema/templates/sistema/api_designer.html",
        "sistema/templates/sistema/integration_center.html",
        "sistema/templates/sistema/dashboard_builder.html",
        "sistema/templates/sistema/validation_center.html",
        "sistema/templates/sistema/release_manager.html",
        "sistema/templates/sistema/environment_manager.html",
        "sistema/templates/sistema/deployment_center.html",
        "sistema/templates/sistema/health_monitoring.html",
        "sistema/templates/sistema/gerar_sistema.html",
    )

    def _read(self, relative_path):
        return (Path(settings.BASE_DIR) / relative_path).read_text(encoding="utf-8")

    def test_shared_header_component_defines_standard_visual_contract(self):
        source = self._read("templates/sistema/_page_header.html")

        self.assertIn("df-page-header", source)
        self.assertIn("linear-gradient", source)
        self.assertIn("back_url", source)
        self.assertIn("secondary_url", source)
        self.assertIn("bi-arrow-left", source)

    def test_system_tools_use_shared_header_and_return_to_workspace(self):
        for template_path in self.TOOL_TEMPLATES:
            with self.subTest(template=template_path):
                source = self._read(template_path)
                self.assertIn("sistema/_page_header.html", source)
                self.assertIn("sistema:workspace", source)
                self.assertIn("Voltar ao Workspace", source)

    def test_designers_no_longer_use_legacy_builder_or_fake_workspace_back(self):
        for template_path in (
            "sistema/templates/sistema/form_designer.html",
            "sistema/templates/sistema/crud_designer.html",
            "sistema/templates/sistema/dashboard_builder.html",
        ):
            with self.subTest(template=template_path):
                self.assertNotIn("Voltar ao Builder", self._read(template_path))

        for template_path in (
            "sistema/templates/sistema/business_rules_designer.html",
            "sistema/templates/sistema/workflow_designer.html",
            "sistema/templates/sistema/permission_designer.html",
            "sistema/templates/sistema/api_designer.html",
            "sistema/templates/sistema/integration_center.html",
        ):
            with self.subTest(template=template_path):
                source = self._read(template_path)
                self.assertNotIn("href=\"{% url 'sistema:lista' %}\" class=\"btn btn-outline-secondary\">Workspace", source)

    def test_generation_success_returns_to_generation_parent(self):
        source = self._read("sistema/templates/sistema/gerar_sucesso.html")

        self.assertIn("sistema:gerar_sistema", source)
        self.assertIn("Voltar para Gerar aplicação", source)
        self.assertIn("sistema:workspace", source)
