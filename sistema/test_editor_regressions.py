from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema


class EditorRegressionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="editor_reg", password="x")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Editor Regression",
            slug="editor-regression",
            caminho_geracao="C:/tmp/editor-regression",
            gerar_api_rest=True,
            usar_custom_user=True,
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="core")
        entidade_destino = Entidade.objects.create(modulo=modulo, nome="Setor", gerar_endpoints_api=False)
        Campo.objects.create(entidade=entidade_destino, nome="nome", tipo="CharField", max_length=100)
        entidade = Entidade.objects.create(modulo=modulo, nome="Funcionario", gerar_endpoints_api=True)
        Campo.objects.create(
            entidade=entidade,
            nome="setor",
            tipo="ForeignKey",
            entidade_relacionada=entidade_destino,
            on_delete="models.PROTECT",
            related_name_str="funcionarios",
            verbose_name="Setor de lotação",
            help_text="Selecione o setor.",
            null=True,
            blank=True,
        )

    def test_editor_exposes_api_rest_and_custom_user_flags(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sistema:editar_sistema", args=[self.sistema.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="apiRest"')
        self.assertContains(response, 'id="customUser"')
        self.assertContains(response, "Gerar API REST")
        self.assertContains(response, "gerar_api_rest")
        self.assertContains(response, "gerar_endpoints_api")

    def test_editor_exposes_advanced_field_configuration(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sistema:editar_sistema", args=[self.sistema.id]))
        self.assertContains(response, "Configurações avançadas")
        self.assertContains(response, "Verbose name")
        self.assertContains(response, "related_name")
        self.assertContains(response, "on_delete")
        self.assertContains(response, "Help text")
        self.assertContains(response, "collapse show field-advanced")

    def test_editor_serialized_payload_contains_saved_advanced_values(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sistema:editar_sistema", args=[self.sistema.id]))
        self.assertContains(response, "Setor de lotação")
        self.assertContains(response, "funcionarios")
        self.assertContains(response, "models.PROTECT")
        self.assertContains(response, "Selecione o setor.")
