from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase

from .compiler import ArtifactWriter, SpecificationCompiler
from .models import Campo, Entidade, Modulo, Sistema
from .specification import build_specification
from .specification_plan import CompilationPlan

User = get_user_model()


class Gen0003CompilerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="gen0003", email="gen0003@example.com", password="secret123"
        )
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema de Teste",
            descricao="Compilador GEN-0003",
        )

    def test_compiler_produces_exact_compilation_plan(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Cadastro")
        entidade = Entidade.objects.create(
            modulo=modulo,
            nome="Pessoa",
            gerar_crud_views=True,
        )
        Campo.objects.create(
            entidade=entidade,
            nome="Nome Completo",
            tipo="CharField",
            max_length=150,
        )

        spec = build_specification(self.sistema)
        plan = CompilationPlan(spec)
        compiled = SpecificationCompiler(spec).compile()

        self.assertEqual(
            {item.path for item in compiled},
            set(plan.paths()),
        )
        self.assertTrue(any(item.path == "cadastro/models.py" for item in compiled))

    def test_compiler_does_not_use_orm_objects_as_context(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Gestão de Pessoas")
        Entidade.objects.create(modulo=modulo, nome="Ordem de Serviço")

        spec = build_specification(self.sistema)
        compiled = SpecificationCompiler(spec).compile()
        models = next(item.content for item in compiled if item.path == "gestao_de_pessoas/models.py")

        self.assertIn("class OrdemDeServico(models.Model):", models)
        self.assertNotIn("campos.all()", models)

    def test_cross_module_relationship_uses_canonical_app_name(self):
        cadastro = Modulo.objects.create(sistema=self.sistema, nome="Cadastro Geral")
        vendas = Modulo.objects.create(sistema=self.sistema, nome="Vendas")
        cliente = Entidade.objects.create(modulo=cadastro, nome="Cliente")
        pedido = Entidade.objects.create(modulo=vendas, nome="Pedido")
        Campo.objects.create(
            entidade=pedido,
            nome="Cliente",
            tipo="ForeignKey",
            entidade_relacionada=cliente,
        )

        spec = build_specification(self.sistema)
        compiled = SpecificationCompiler(spec).compile()
        models = next(item.content for item in compiled if item.path == "vendas/models.py")

        self.assertIn("from cadastro_geral.models import Cliente", models)
        self.assertIn('"cadastro_geral.Cliente"', models)

    def test_writer_is_confined_to_output_directory(self):
        with TemporaryDirectory() as tmp:
            writer = ArtifactWriter(Path(tmp) / "project")
            artifact = type("Artifact", (), {
                "path": "../escape.py",
                "content": "# unsafe",
            })()
            with self.assertRaises(ValueError):
                writer.write((artifact,))
