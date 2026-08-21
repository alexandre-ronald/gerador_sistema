from types import SimpleNamespace

from django.test import SimpleTestCase

from .services import GeradorService


class GeradorServiceRelationTests(SimpleTestCase):
    def test_is_relation_uses_campo_tipo_without_tipo_python(self):
        """Relation detection must use the persisted Campo.tipo field."""
        for tipo in ("ForeignKey", "OneToOneField", "ManyToManyField"):
            campo = SimpleNamespace(tipo=tipo)

            self.assertTrue(GeradorService._is_relation(campo))
            self.assertFalse(hasattr(campo, "tipo_python"))

    def test_is_relation_rejects_non_relation_without_tipo_python(self):
        campo = SimpleNamespace(tipo="CharField")

        self.assertFalse(GeradorService._is_relation(campo))
        self.assertFalse(hasattr(campo, "tipo_python"))

    def test_preparar_entidade_still_materializes_tipo_python_for_templates(self):
        """tipo_python remains a compiler/template context value, not a model field."""
        entidade_relacionada = SimpleNamespace(nome="Departamento")
        campo = SimpleNamespace(
            nome="Departamento",
            tipo="ForeignKey",
            verbose_name="",
            default_value="",
            related_name_str="",
            upload_to="",
            on_delete="models.CASCADE",
            entidade_relacionada=entidade_relacionada,
        )
        entidade = SimpleNamespace(
            nome="Funcionario",
            nome_plural="Funcionários",
            campos=SimpleNamespace(all=lambda: [campo]),
        )

        service = object.__new__(GeradorService)
        service._preparar_entidade(entidade)

        self.assertEqual(campo.tipo_python, "ForeignKey")
        self.assertEqual(campo.classe_relacionada, "Departamento")
