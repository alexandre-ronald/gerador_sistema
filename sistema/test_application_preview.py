from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .application_preview import build_preview_shell
from .models import Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationPreviewShellTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="preview", password="test123")
        self.other = get_user_model().objects.create_user(username="other", password="test123")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Gestão de Contratos",
            tipo_menu="lateral",
            interface_modo="escuro",
            interface_densidade="compacta",
            interface_nome="Contratos 360",
            interface_cor_primaria="#2563eb",
            interface_cor_destaque="#7c3aed",
            interface_breadcrumb=True,
            interface_busca=True,
            interface_menu_usuario=True,
        )
        contratos = Modulo.objects.create(sistema=self.sistema, nome="Contratos")
        cadastros = Modulo.objects.create(sistema=self.sistema, nome="Cadastros")
        Entidade.objects.create(modulo=contratos, nome="Contrato", nome_plural="Contratos", gerar_crud_views=True)
        Entidade.objects.create(modulo=cadastros, nome="Fornecedor", nome_plural="Fornecedores", gerar_crud_views=True)
        Entidade.objects.create(modulo=cadastros, nome="Interno", nome_plural="Internos", gerar_crud_views=False)
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={"forms": {}})

    def test_projects_interface_designer_into_preview_shell(self):
        preview = build_preview_shell(self.sistema)
        self.assertEqual(preview["application"]["name"], "Contratos 360")
        self.assertEqual(preview["interface"]["menu"], "lateral")
        self.assertEqual(preview["interface"]["mode"], "escuro")
        self.assertEqual(preview["interface"]["density"], "compacta")
        self.assertEqual(preview["interface"]["primary"], "#2563eb")
        self.assertEqual(preview["interface"]["accent"], "#7c3aed")
        self.assertTrue(preview["interface"]["breadcrumb"])
        self.assertTrue(preview["interface"]["search"])
        self.assertTrue(preview["interface"]["user_menu"])

    def test_navigation_is_deterministic_and_matches_generated_crud_scope(self):
        first = build_preview_shell(self.sistema)
        second = build_preview_shell(self.sistema)
        self.assertEqual(first, second)
        modules = first["navigation"]["modules"]
        self.assertEqual([item["label"] for item in modules], ["Cadastros", "Contratos"])
        self.assertEqual([item["label"] for item in modules[0]["items"]], ["Fornecedores"])
        self.assertEqual([item["label"] for item in modules[1]["items"]], ["Contratos"])
        self.assertNotIn("Internos", str(modules))

    def test_preview_does_not_persist_parallel_contract(self):
        build_preview_shell(self.sistema)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertNotIn("preview", draft.estrutura_json)
        self.assertNotIn("preview_studio", draft.estrutura_json)

    def test_preview_view_renders_shell_for_owner(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sistema:application_preview", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Preview Studio")
        self.assertContains(response, "Contratos 360")
        self.assertContains(response, "application-preview-shell")
        self.assertContains(response, "Fornecedores")
        self.assertContains(response, "Contratos")
        self.assertNotContains(response, ">Internos<")

    def test_preview_view_is_scoped_to_owner(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("sistema:application_preview", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 404)
