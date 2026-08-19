from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import TestCase, SimpleTestCase

from .compiler import ArtifactWriter, SpecificationCompiler
from .generation_export import _installation_bat
from .generation_validation import validate_generated_project
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
        entidade = Entidade.objects.create(modulo=modulo, nome="Pessoa", gerar_crud_views=True)
        Campo.objects.create(entidade=entidade, nome="Nome Completo", tipo="CharField", max_length=150)

        spec = build_specification(self.sistema)
        plan = CompilationPlan(spec)
        compiled = SpecificationCompiler(spec).compile()

        self.assertEqual({item.path for item in compiled}, set(plan.paths()))
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
        Campo.objects.create(entidade=pedido, nome="Cliente", tipo="ForeignKey", entidade_relacionada=cliente)

        spec = build_specification(self.sistema)
        compiled = SpecificationCompiler(spec).compile()
        models = next(item.content for item in compiled if item.path == "vendas/models.py")

        self.assertNotIn("from cadastro_geral.models import Cliente", models)
        self.assertIn('"cadastro_geral.Cliente"', models)

    def test_writer_is_confined_to_output_directory(self):
        with TemporaryDirectory() as tmp:
            writer = ArtifactWriter(Path(tmp) / "project")
            artifact = type("Artifact", (), {"path": "../escape.py", "content": "# unsafe"})()
            with self.assertRaises(ValueError):
                writer.write((artifact,))

    def test_generated_project_passes_structural_validation(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Gestão de Pessoas")
        Entidade.objects.create(modulo=modulo, nome="Funcionário")

        spec = build_specification(self.sistema)
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "project"
            SpecificationCompiler(spec).write(output)
            validated = validate_generated_project(spec, output)

        self.assertEqual(set(validated), set(CompilationPlan(spec).paths()))

    def test_generated_project_validation_rejects_missing_artifact(self):
        spec = build_specification(self.sistema)
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "project"
            SpecificationCompiler(spec).write(output)
            (output / "manage.py").unlink()

            with self.assertRaises(ValidationError) as context:
                validate_generated_project(spec, output)

        self.assertIn("Artefato ausente: manage.py", str(context.exception))

    def test_base_and_index_materialize_modules_and_entities(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Gestão de Pessoas")
        Entidade.objects.create(modulo=modulo, nome="Funcionário", gerar_crud_views=True)

        spec = build_specification(self.sistema)
        compiled = SpecificationCompiler(spec).compile()
        base = next(item.content for item in compiled if item.path == "templates/base.html")
        index = next(item.content for item in compiled if item.path == "templates/index.html")

        self.assertIn("Gestão de Pessoas", base)
        self.assertIn("Funcionário", base)
        self.assertIn("gestao_de_pessoas:funcionario_list", base)
        self.assertIn("Gestão de Pessoas", index)
        self.assertIn("Funcionário", index)
        self.assertIn("gestao_de_pessoas:funcionario_list", index)
        self.assertNotIn("sistema.modulos.all", base)
        self.assertNotIn("sistema.modulos.all", index)

    def test_crud_html_templates_are_materialized_for_generated_entity(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Gestão de Pessoas")
        entidade = Entidade.objects.create(modulo=modulo, nome="Funcionário", gerar_crud_views=True)
        Campo.objects.create(entidade=entidade, nome="Nome Completo", tipo="CharField", max_length=150)

        spec = build_specification(self.sistema)
        compiled = SpecificationCompiler(spec).compile()
        paths = {item.path: item.content for item in compiled}

        expected = {
            "gestao_de_pessoas/templates/gestao_de_pessoas/funcionario_list.html",
            "gestao_de_pessoas/templates/gestao_de_pessoas/funcionario_form.html",
            "gestao_de_pessoas/templates/gestao_de_pessoas/funcionario_confirm_delete.html",
        }
        self.assertTrue(expected.issubset(paths))
        self.assertIn("Gerenciamento de Funcionário", paths["gestao_de_pessoas/templates/gestao_de_pessoas/funcionario_list.html"])

    def test_static_directory_is_materialized(self):
        spec = build_specification(self.sistema)
        compiled = SpecificationCompiler(spec).compile()
        static = next(item for item in compiled if item.path == "static/.gitkeep")
        self.assertEqual(static.kind, "static")
        self.assertEqual(static.content, "")


class Gen0003TemplateAndWindowsTests(SimpleTestCase):
    def test_settings_uses_technical_module_name(self):
        context = {
            "sistema": SimpleNamespace(
                modulos=SimpleNamespace(all=lambda: [SimpleNamespace(nome="Gestão de Pessoas", nome_tecnico="gestao_de_pessoas")]),
                banco_dados="sqlite3",
            ),
            "nome_projeto": "sistema_de_gestao_hospitalar",
        }
        rendered = render_to_string("gerador/snippets/settings.txt", context)
        self.assertIn('"gestao_de_pessoas",', rendered)
        self.assertNotIn('"gestao-de-pessoas",', rendered)

    def test_root_urls_keep_public_slug_but_import_technical_name(self):
        context = {
            "sistema": SimpleNamespace(
                modulos=SimpleNamespace(all=lambda: [SimpleNamespace(nome="Gestão de Pessoas", nome_tecnico="gestao_de_pessoas")])
            )
        }
        rendered = render_to_string("gerador/snippets/urls_root.txt", context)
        self.assertIn('"gestao-de-pessoas/"', rendered)
        self.assertIn('include("gestao_de_pessoas.urls")', rendered)

    def test_installation_bat_has_no_residual_text_and_uses_utf8_codepage(self):
        content = _installation_bat("Sistema de Gestão Hospitalar")
        self.assertIn("chcp 65001 >nul", content)
        self.assertIn(r"call .venv\Scripts\activate.bat", content)
        self.assertNotIn("Salvador:", content)
        self.assertIn("Sistema de Gestão Hospitalar", content)

    def test_installation_bat_is_written_with_utf8_bom(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "instalacao.bat"
            path.write_text(_installation_bat("Gestão de Pessoas"), encoding="utf-8-sig", newline="\r\n")
            raw = path.read_bytes()

        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Gestão de Pessoas".encode("utf-8"), raw)
