from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationPreviewRoleToolbarTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="role_toolbar", password="x")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Gestão de Contratos",
            slug="gestao-contratos-role-toolbar",
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Contratos")
        self.entidade = Entidade.objects.create(
            modulo=modulo,
            nome="Contrato",
            nome_plural="Contratos",
            gerar_crud_views=True,
        )
        Campo.objects.create(entidade=self.entidade, nome="codigo", tipo="CharField", max_length=30)
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "rbac": {
                    "enabled": True,
                    "roles": [
                        {"id": "consulta", "label": "Consulta", "description": "Somente consulta", "group": "Consulta", "order": 0},
                    ],
                    "entities": {
                        "Contrato": {
                            "roles": {"consulta": ["list", "view"]},
                            "transitions": {},
                        }
                    },
                }
            },
        )
        self.client.force_login(self.user)

    def test_main_preview_renders_role_selector_and_selected_role(self):
        response = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk]),
            {"entidade": self.entidade.pk, "papel": "consulta"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-preview-role-toolbar')
        self.assertContains(response, 'data-preview-role-select')
        self.assertContains(response, 'value="consulta" selected')
        self.assertContains(response, 'data-preview-active-role="consulta"')
        self.assertContains(response, "Simulando <strong>Consulta</strong>", html=True)
        self.assertNotContains(response, ">Novo<")
        self.assertNotContains(response, 'title="Editar"')
        self.assertNotContains(response, 'title="Excluir"')
        self.assertContains(response, 'title="Visualizar"')

    def test_invalid_role_is_visible_and_fail_closed_in_main_preview(self):
        response = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk]),
            {"entidade": self.entidade.pk, "papel": "papel_inventado"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-preview-invalid-role')
        self.assertContains(response, "Papel inválido: papel_inventado")
        self.assertContains(response, "modo fail-closed")
        self.assertNotContains(response, ">Novo<")
        self.assertNotContains(response, 'title="Visualizar"')
        self.assertNotContains(response, 'title="Editar"')
        self.assertNotContains(response, 'title="Excluir"')
