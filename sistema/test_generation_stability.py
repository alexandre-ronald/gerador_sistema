import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase

from sistema.models import Entidade, Modulo, Sistema, VersaoGeracao
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

    def test_successful_generation_creates_version_snapshot(self):
        root = tempfile.mkdtemp(prefix="gen_version_")
        sistema = Sistema.objects.create(usuario=self.user, nome="Sistema Versionado", caminho_geracao=root)
        modulo = Modulo.objects.create(sistema=sistema, nome="Cadastro")
        entidade = Entidade.objects.create(modulo=modulo, nome="Cliente")
        from sistema.models import Campo
        Campo.objects.create(entidade=entidade, nome="nome", tipo="CharField", max_length=120, verbose_name="Nome completo", help_text="Nome do cliente")

        GeradorService(sistema.pk).gerar_projeto_completo()
        GeradorService(sistema.pk).gerar_projeto_completo()

        versoes = list(VersaoGeracao.objects.filter(sistema=sistema).order_by("numero"))
        self.assertEqual([v.numero for v in versoes], [1, 2])
        self.assertEqual(versoes[0].estrutura_json["sistema"]["caminho_geracao"], root)
        campo = versoes[0].estrutura_json["modulos"][0]["entidades"][0]["campos"][0]
        self.assertEqual(campo["verbose_name"], "Nome completo")
        self.assertEqual(campo["help_text"], "Nome do cliente")

    def test_failed_generation_does_not_create_version(self):
        root = tempfile.mkdtemp(prefix="gen_failed_version_")
        sistema = Sistema.objects.create(usuario=self.user, nome="Sistema Inválido", caminho_geracao=root)
        Modulo.objects.create(sistema=sistema, nome="Gestão")
        Modulo.objects.create(sistema=sistema, nome="Gestao")

        with self.assertRaises(ValueError):
            GeradorService(sistema.pk).gerar_projeto_completo()

        self.assertFalse(VersaoGeracao.objects.filter(sistema=sistema).exists())

    def test_docker_generation_creates_complete_docker_artifacts(self):
        root = tempfile.mkdtemp(prefix="gen_docker_")
        sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema Docker",
            caminho_geracao=root,
            gerar_docker=True,
        )
        Modulo.objects.create(sistema=sistema, nome="Cadastro")

        GeradorService(sistema.pk).gerar_projeto_completo()

        self.assertTrue(Path(root, "Dockerfile").is_file())
        self.assertTrue(Path(root, "docker-compose.yml").is_file())
        env_example = Path(root, ".env.example")
        self.assertTrue(env_example.is_file())
        self.assertIn("DJANGO_SECRET_KEY=", env_example.read_text(encoding="utf-8"))
