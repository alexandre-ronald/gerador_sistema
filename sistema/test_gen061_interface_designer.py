from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Sistema


class InterfaceDesignerViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="interface061", password="teste123")
        self.outro = User.objects.create_user(username="outro061", password="teste123")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema de Contratos",
            descricao="Controle de contratos",
            caminho_geracao="C:/tmp/contratos",
        )
        self.url = reverse("sistema:interface_designer", args=[self.sistema.pk])
        self.client.login(username="interface061", password="teste123")

    def test_abre_interface_designer(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Interface Designer")
        self.assertContains(response, "Salvar interface")
        self.assertContains(response, "previewApp")

    def test_salva_configuracao_visual(self):
        response = self.client.post(self.url, {
            "tipo_menu": "superior",
            "interface_modo": "escuro",
            "interface_densidade": "compacta",
            "interface_nome": "Contratos HU",
            "interface_cor_primaria": "#123456",
            "interface_cor_destaque": "#abcdef",
            "interface_breadcrumb": "on",
            "interface_menu_usuario": "on",
        })
        self.assertRedirects(response, self.url)
        self.sistema.refresh_from_db()
        self.assertEqual(self.sistema.tipo_menu, "superior")
        self.assertEqual(self.sistema.interface_modo, "escuro")
        self.assertEqual(self.sistema.interface_densidade, "compacta")
        self.assertEqual(self.sistema.interface_nome, "Contratos HU")
        self.assertEqual(self.sistema.interface_cor_primaria, "#123456")
        self.assertEqual(self.sistema.interface_cor_destaque, "#abcdef")
        self.assertTrue(self.sistema.interface_breadcrumb)
        self.assertFalse(self.sistema.interface_busca)
        self.assertTrue(self.sistema.interface_menu_usuario)

    def test_usuario_nao_acessa_interface_de_outro_usuario(self):
        outro_sistema = Sistema.objects.create(
            usuario=self.outro,
            nome="Sistema Privado",
            caminho_geracao="C:/tmp/privado",
        )
        response = self.client.get(reverse("sistema:interface_designer", args=[outro_sistema.pk]))
        self.assertEqual(response.status_code, 404)
