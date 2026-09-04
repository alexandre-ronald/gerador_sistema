import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Modulo, Sistema
from .structure_service import serialize_system_structure


class NovoSistemaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="creator", password="x")
        self.client.force_login(self.user)

    def test_new_system_page_is_user_oriented(self):
        response = self.client.get(reverse("sistema:criar"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O que você precisa construir?")
        self.assertContains(response, "O que este sistema precisa resolver?")
        self.assertContains(response, "Cadastro e Controle")
        self.assertContains(response, "Solicitações e Workflow")
        self.assertContains(response, "Gestão e Acompanhamento")
        self.assertContains(response, "Começar vazio")

    def test_creates_system_and_redirects_to_contextual_editor(self):
        response = self.client.post(reverse("sistema:criar"), {
            "nome": "Gestão de Contratos",
            "descricao": "Controlar contratos, fiscais e vencimentos.",
            "tipo_sistema": Sistema.TIPO_CADASTRO,
        })
        sistema = Sistema.objects.get(nome="Gestão de Contratos")
        expected = reverse("sistema:editar_sistema", args=[sistema.pk]) + "?novo=1"
        self.assertRedirects(response, expected)
        self.assertEqual(sistema.usuario, self.user)
        self.assertEqual(sistema.tipo_sistema, Sistema.TIPO_CADASTRO)
        self.assertEqual(sistema.descricao, "Controlar contratos, fiscais e vencimentos.")
        self.assertEqual(sistema.caminho_geracao, os.path.join(str(settings.BASE_DIR), "projetos_gerados"))

    def test_first_editor_entry_exposes_user_context(self):
        sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Gestão de Contratos",
            descricao="Controlar contratos e vencimentos",
            tipo_sistema=Sistema.TIPO_GESTAO,
            caminho_geracao="/tmp/projeto",
        )
        response = self.client.get(reverse("sistema:editar_sistema", args=[sistema.pk]) + "?novo=1")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["primeira_configuracao"])
        self.assertEqual(response.context["tipo_sistema_label"], "Gestão e Acompanhamento")
        self.assertEqual(response.context["sistema"].descricao, "Controlar contratos e vencimentos")

    def test_existing_system_does_not_enter_first_configuration_mode(self):
        sistema = Sistema.objects.create(usuario=self.user, nome="Existente", caminho_geracao="/tmp/projeto")
        Modulo.objects.create(sistema=sistema, nome="cadastros")
        response = self.client.get(reverse("sistema:editar_sistema", args=[sistema.pk]) + "?novo=1")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["primeira_configuracao"])

    def test_invalid_type_does_not_create_system(self):
        response = self.client.post(reverse("sistema:criar"), {"nome": "Sistema Inválido", "descricao": "Teste", "tipo_sistema": "nao-existe"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Sistema.objects.filter(nome="Sistema Inválido").exists())

    def test_name_is_required(self):
        response = self.client.post(reverse("sistema:criar"), {"nome": "", "descricao": "Sem nome", "tipo_sistema": Sistema.TIPO_VAZIO})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Sistema.objects.count(), 0)

    def test_purpose_is_preserved_by_structure_serialization(self):
        sistema = Sistema.objects.create(usuario=self.user, nome="Solicitações", descricao="Fluxo de solicitações internas", tipo_sistema=Sistema.TIPO_WORKFLOW, caminho_geracao="/tmp/projeto")
        estrutura = serialize_system_structure(sistema)
        self.assertEqual(estrutura["sistema"]["tipo_sistema"], Sistema.TIPO_WORKFLOW)
        self.assertEqual(estrutura["sistema"]["descricao"], "Fluxo de solicitações internas")
