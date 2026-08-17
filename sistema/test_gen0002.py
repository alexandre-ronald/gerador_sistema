from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Campo, Entidade, Modulo, Sistema
from .services import GeradorService
from .specification import SPECIFICATION_VERSION, build_specification
from .specification_plan import CompilationPlan

User = get_user_model()


class Gen0002SpecificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="gen0002", email="gen0002@example.com", password="secret123"
        )
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema de Gestão",
            descricao="Teste da especificação canônica",
        )

    def test_builds_canonical_specification(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Gestão de Pessoas")
        entidade = Entidade.objects.create(
            modulo=modulo,
            nome="Ordem de Serviço",
            nome_plural="Ordens de Serviço",
            gerar_crud_views=True,
        )
        Campo.objects.create(
            entidade=entidade,
            nome="Descrição",
            tipo="CharField",
            max_length=200,
        )

        spec = build_specification(self.sistema)

        self.assertEqual(spec.version, SPECIFICATION_VERSION)
        self.assertEqual(spec.technical_name, "sistema_de_gestao")
        self.assertEqual(spec.modules[0].technical_name, "gestao_de_pessoas")
        self.assertEqual(spec.modules[0].entities[0].class_name, "OrdemDeServico")
        self.assertEqual(spec.modules[0].entities[0].fields[0].technical_name, "descricao")
        self.assertEqual(len(spec.fingerprint), 64)

    def test_fingerprint_is_deterministic(self):
        first = build_specification(self.sistema)
        second = build_specification(self.sistema)
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(first.canonical_json(), second.canonical_json())

    def test_compilation_plan_does_not_write_files(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Cadastro")
        Entidade.objects.create(modulo=modulo, nome="Pessoa", gerar_crud_views=True)

        plan = GeradorService(self.sistema.id).plano_compilacao()
        paths = plan.paths()

        self.assertIn("manage.py", paths)
        self.assertIn("cadastro/models.py", paths)
        self.assertIn("cadastro/templates/cadastro/pessoa_list.html", paths)
        self.assertNotIn("Dockerfile", paths)

    def test_docker_artifacts_are_conditional(self):
        self.sistema.gerar_docker = True
        self.sistema.save(update_fields=["gerar_docker"])

        plan = CompilationPlan(build_specification(self.sistema))
        self.assertIn("Dockerfile", plan.paths())
        self.assertIn("docker-compose.yml", plan.paths())
        self.assertIn(".dockerignore", plan.paths())

    def test_invalid_specification_is_rejected_before_conversion(self):
        self.sistema.usar_custom_user = True
        self.sistema.save(update_fields=["usar_custom_user"])

        with self.assertRaises(ValidationError):
            build_specification(self.sistema)

    def test_text_fields_receive_safe_max_length_default(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Cadastro")
        entidade = Entidade.objects.create(modulo=modulo, nome="Funcionario")

        for tipo in ("CharField", "EmailField", "URLField"):
            campo = Campo.objects.create(
                entidade=entidade,
                nome=f"campo_{tipo}",
                tipo=tipo,
            )
            self.assertEqual(campo.max_length, 255)

    def test_custom_user_is_disabled_by_default(self):
        self.assertFalse(self.sistema.usar_custom_user)
