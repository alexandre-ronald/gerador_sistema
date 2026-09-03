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
