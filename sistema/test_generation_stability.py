import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase

from sistema.models import Entidade, Modulo, Sistema
from sistema.services import GeradorService


class GenerationStabilityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="gen-test", password="senha123")

    def test_login_is_generated_once_even_without_crud_entities(self):
        root = tempfile.mkdtemp(prefix="gen_stable_")
        sistema = Sistema.objects.create(usuario=self.user, nome="Sistema Sem CRUD", caminho_geracao=root)
        Modulo.objects.create(sistema=sistema, nome="configuracao")
        GeradorService(sistema.pk).gerar_projeto_completo()
        self.assertTrue(Path(root, "templates", "registration", "login.html").is_file())

    def test_python_identifier_collision_is_rejected_before_compilation(self):
        root = tempfile.mkdtemp(prefix="gen_collision_")
        sistema = Sistema.objects.create(usuario=self.user, nome="Sistema", caminho_geracao=root)
        Modulo.objects.create(sistema=sistema, nome="Gestão")
        Modulo.objects.create(sistema=sistema, nome="Gestao")
        with self.assertRaises(ValueError) as ctx:
            GeradorService(sistema.pk).gerar_projeto_completo()
        self.assertIn("mesmo app Python", str(ctx.exception))

    def test_generated_project_with_real_crud_keeps_permission_contract(self):
        root = tempfile.mkdtemp(prefix="gen_crud_")
        sistema = Sistema.objects.create(usuario=self.user, nome="Sistema CRUD", caminho_geracao=root)
        modulo = Modulo.objects.create(sistema=sistema, nome="Cadastro")
        entidade = Entidade.objects.create(modulo=modulo, nome="Funcionário", gerar_crud_views=True)
        from sistema.models import Campo
        Campo.objects.create(entidade=entidade, nome="nome", tipo="CharField", max_length=120)
        logs = GeradorService(sistema.pk).gerar_projeto_completo()
        self.assertTrue(any("navegação" in item.lower() for item in logs))
        base = Path(root, "templates", "base.html").read_text(encoding="utf-8")
        self.assertIn("navigation_modules", base)
        self.assertIn("data-permission", base)
