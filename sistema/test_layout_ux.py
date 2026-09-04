from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Sistema


class LayoutUXNavigationContractTests(TestCase):
    def _read(self, path):
        return Path(path).read_text(encoding="utf-8")

    def test_model_designer_uses_standard_page_header_and_contextual_back(self):
        source = self._read("templates/sistema/editor.html")

        self.assertIn('sistema/_page_header.html', source)
        self.assertIn("{% if sistema_id %}", source)
        self.assertIn("{% url 'sistema:workspace' sistema_id as model_back_url %}", source)
        self.assertIn('back_label="Voltar ao Workspace"', source)
        self.assertIn("{% url 'sistema:lista' as model_back_url %}", source)
        self.assertIn('back_label="Voltar a Meus Sistemas"', source)

    def test_model_designer_views_expose_system_context_when_editing(self):
        user = get_user_model().objects.create_user(username="model-layout", password="senha-forte")
        sistema = Sistema.objects.create(usuario=user, nome="Model UX")
        self.client.force_login(user)

        create_response = self.client.get(reverse("sistema:criar"))
        edit_response = self.client.get(reverse("sistema:editar_sistema", args=[sistema.pk]))

        self.assertEqual(create_response.status_code, 200)
        self.assertTemplateUsed(create_response, "sistema/novo_sistema.html")
        self.assertContains(create_response, "Voltar a Meus Sistemas")

        self.assertEqual(edit_response.context["sistema"], sistema)
        self.assertContains(edit_response, "Voltar ao Workspace")

    def test_designers_no_longer_use_legacy_builder_or_fake_workspace_back(self):
        for template_path in (
            "sistema/templates/sistema/form_designer.html",
            "sistema/templates/sistema/crud_designer.html",
            "sistema/templates/sistema/dashboard_builder.html",
        ):
            with self.subTest(template=template_path):
                self.assertNotIn("Voltar ao Builder", self._read(template_path))
