from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.test import TestCase

from .compiler import SpecificationCompiler
from .models import Campo, Entidade, Modulo, Sistema
from .specification import build_specification
from .validation import validate_specification


class Gen0011RelationshipTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(
            username="gen0011", password="secret123"
        )
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema Relacional GEN-0011",
        )

    def test_foreign_key_cross_module_uses_string_reference_without_import(self):
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

        self.assertIn('"cadastro_geral.Cliente"', models)
        self.assertNotIn("from cadastro_geral.models import Cliente", models)

    def test_many_to_many_does_not_emit_on_delete(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Cadastro")
        grupo = Entidade.objects.create(modulo=modulo, nome="Grupo")
        usuario = Entidade.objects.create(modulo=modulo, nome="Usuario")
        Campo.objects.create(
            entidade=usuario,
            nome="Grupos",
            tipo="ManyToManyField",
            entidade_relacionada=grupo,
        )

        spec = build_specification(self.sistema)
        compiled = SpecificationCompiler(spec).compile()
        models = next(item.content for item in compiled if item.path == "cadastro/models.py")

        field_start = models.index("grupos = models.ManyToManyField")
        field_block = models[field_start : models.index("\n", field_start + 1) + 500]
        self.assertNotIn("on_delete=", field_block)

    def test_set_null_requires_null_true(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Cadastro")
        cliente = Entidade.objects.create(modulo=modulo, nome="Cliente")
        pedido = Entidade.objects.create(modulo=modulo, nome="Pedido")
        Campo.objects.create(
            entidade=pedido,
            nome="Cliente",
            tipo="ForeignKey",
            entidade_relacionada=cliente,
            on_delete="models.SET_NULL",
            null=False,
        )

        with self.assertRaises(ValidationError) as context:
            validate_specification(self.sistema)

        self.assertIn("usa SET_NULL e precisa de null=True", str(context.exception))

    def test_many_to_many_rejects_null(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Cadastro")
        grupo = Entidade.objects.create(modulo=modulo, nome="Grupo")
        usuario = Entidade.objects.create(modulo=modulo, nome="Usuario")
        Campo.objects.create(
            entidade=usuario,
            nome="Grupos",
            tipo="ManyToManyField",
            entidade_relacionada=grupo,
            null=True,
        )

        with self.assertRaises(ValidationError) as context:
            validate_specification(self.sistema)

        self.assertIn("ManyToManyField 'Usuario.Grupos' não aceita null=True", str(context.exception))

    def test_related_name_must_be_python_identifier(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Cadastro")
        cliente = Entidade.objects.create(modulo=modulo, nome="Cliente")
        pedido = Entidade.objects.create(modulo=modulo, nome="Pedido")
        Campo.objects.create(
            entidade=pedido,
            nome="Cliente",
            tipo="ForeignKey",
            entidade_relacionada=cliente,
            related_name="cliente-pedidos",
        )

        with self.assertRaises(ValidationError) as context:
            validate_specification(self.sistema)

        self.assertIn("related_name inválido", str(context.exception))

    def test_relation_to_entity_from_other_system_is_rejected(self):
        from django.contrib.auth import get_user_model

        other_user = get_user_model().objects.create_user(
            username="gen0011-other", password="secret123"
        )
        other_system = Sistema.objects.create(
            usuario=other_user,
            nome="Outro Sistema GEN-0011",
        )
        other_module = Modulo.objects.create(sistema=other_system, nome="Outro")
        external = Entidade.objects.create(modulo=other_module, nome="Externa")

        module = Modulo.objects.create(sistema=self.sistema, nome="Cadastro")
        local = Entidade.objects.create(modulo=module, nome="Local")
        Campo.objects.create(
            entidade=local,
            nome="Externa",
            tipo="ForeignKey",
            entidade_relacionada=external,
        )

        with self.assertRaises(ValidationError) as context:
            validate_specification(self.sistema)

        self.assertIn("aponta para uma entidade de outro sistema", str(context.exception))

    def test_generated_models_compile_with_self_relation(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Organização")
        pessoa = Entidade.objects.create(modulo=modulo, nome="Pessoa")
        Campo.objects.create(
            entidade=pessoa,
            nome="Superior",
            tipo="ForeignKey",
            entidade_relacionada=pessoa,
            null=True,
            blank=True,
            on_delete="models.SET_NULL",
            related_name="subordinados",
        )

        spec = build_specification(self.sistema)
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "project"
            SpecificationCompiler(spec).write(output)
            models_path = output / "organizacao" / "models.py"
            content = models_path.read_text(encoding="utf-8")

        self.assertIn('"organizacao.Pessoa"', content)
        self.assertIn('related_name="subordinados"', content)
