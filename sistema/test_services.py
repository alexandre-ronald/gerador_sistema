from pathlib import Path
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

    def test_preparar_entidade_keeps_same_compiled_field_instances(self):
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
        campo.entidade = entidade

        service = object.__new__(GeradorService)
        service._preparar_entidade(entidade)

        self.assertEqual(campo.tipo_python, "ForeignKey")
        self.assertEqual(campo.classe_relacionada, "Departamento")
        self.assertIs(entidade.campos_compilados[0], campo)
        self.assertEqual(entidade.campos_compilados[0].codigo_nome, "departamento")

    def test_preparar_modulos_keeps_same_compiled_entity_instances(self):
        campo = SimpleNamespace(
            nome="Nome",
            tipo="CharField",
            verbose_name="",
            default_value="",
            related_name_str="",
            upload_to="",
            on_delete="models.CASCADE",
            entidade_relacionada=None,
        )
        entidade = SimpleNamespace(
            nome="Eleicao",
            nome_plural="Eleições",
            campos=SimpleNamespace(all=lambda: [campo]),
        )
        campo.entidade = entidade
        modulo = SimpleNamespace(
            nome="Eleição",
            entidades=SimpleNamespace(all=lambda: [entidade]),
        )
        service = object.__new__(GeradorService)
        service.sistema = SimpleNamespace(
            modulos=SimpleNamespace(prefetch_related=lambda *_args: [modulo])
        )
        modulos = service._preparar_modulos()

        self.assertIs(modulos[0].entidades_compiladas[0], entidade)
        self.assertIs(entidade.campos_compilados[0], campo)
        self.assertEqual(entidade.codigo_nome, "eleicao")
        self.assertEqual(campo.codigo_nome, "nome")

    def test_preparar_entidade_rejects_invalid_field_type_before_rendering(self):
        entidade = SimpleNamespace(nome="Eleicao", nome_plural="Eleições")
        campo = SimpleNamespace(
            nome="Status",
            tipo="",
            verbose_name="",
            default_value="",
            related_name_str="",
            upload_to="",
            on_delete="models.CASCADE",
            entidade_relacionada=None,
            entidade=entidade,
        )
        entidade.campos = SimpleNamespace(all=lambda: [campo])

        service = object.__new__(GeradorService)
        with self.assertRaises(ValueError) as exc:
            service._preparar_entidade(entidade)
        self.assertIn("Tipo de campo inválido", str(exc.exception))

    def test_preparar_entidade_rejects_invalid_related_name(self):
        entidade = SimpleNamespace(nome="Funcionario", nome_plural="Funcionários")
        campo = SimpleNamespace(
            nome="Departamento",
            tipo="ForeignKey",
            verbose_name="",
            default_value="",
            related_name_str="departamentos dos funcionarios",
            upload_to="",
            on_delete="models.CASCADE",
            entidade_relacionada=SimpleNamespace(nome="Departamento"),
            entidade=entidade,
        )
        entidade.campos = SimpleNamespace(all=lambda: [campo])

        service = object.__new__(GeradorService)
        with self.assertRaises(ValueError) as exc:
            service._preparar_entidade(entidade)
        self.assertIn("related_name inválido", str(exc.exception))

    def test_preparar_entidade_accepts_related_name_plus(self):
        entidade = SimpleNamespace(nome="Funcionario", nome_plural="Funcionários")
        campo = SimpleNamespace(
            nome="Departamento",
            tipo="ForeignKey",
            verbose_name="",
            default_value="",
            related_name_str="departamentos+",
            upload_to="",
            on_delete="models.CASCADE",
            entidade_relacionada=SimpleNamespace(nome="Departamento"),
            entidade=entidade,
        )
        entidade.campos = SimpleNamespace(all=lambda: [campo])

        service = object.__new__(GeradorService)
        service._preparar_entidade(entidade)
        self.assertEqual(campo.related_name_python, "'departamentos+'")

    def test_preparar_modulos_rejects_app_name_collision_after_normalization(self):
        modulo_a = SimpleNamespace(nome="Gestão", entidades=SimpleNamespace(all=lambda: []))
        modulo_b = SimpleNamespace(nome="Gestao", entidades=SimpleNamespace(all=lambda: []))
        service = object.__new__(GeradorService)
        service.sistema = SimpleNamespace(
            modulos=SimpleNamespace(prefetch_related=lambda *_args: [modulo_a, modulo_b])
        )

        with self.assertRaises(ValueError) as exc:
            service._preparar_modulos()
        self.assertIn("Colisão de nome de app", str(exc.exception))

    def test_preparar_modulos_rejects_class_name_collision_after_normalization(self):
        def entity(name):
            return SimpleNamespace(
                nome=name,
                nome_plural=name,
                campos=SimpleNamespace(all=lambda: []),
            )

        entidade_a = entity("Eleição")
        entidade_b = entity("Eleicao")
        modulo = SimpleNamespace(
            nome="Votação",
            entidades=SimpleNamespace(all=lambda: [entidade_a, entidade_b]),
        )
        service = object.__new__(GeradorService)
        service.sistema = SimpleNamespace(
            modulos=SimpleNamespace(prefetch_related=lambda *_args: [modulo])
        )

        with self.assertRaises(ValueError) as exc:
            service._preparar_modulos()
        self.assertIn("Colisão de classe", str(exc.exception))

    def test_class_name_normalizes_accents_and_spaces(self):
        self.assertEqual(GeradorService._class_name("Eleição"), "Eleicao")
        self.assertEqual(GeradorService._class_name("Funcionário Público"), "FuncionarioPublico")


class GeradorServiceArtifactRegressionTests(SimpleTestCase):
    def _snippet(self, name):
        return (
            Path(__file__).resolve().parent
            / "templates"
            / "gerador"
            / "snippets"
            / name
        ).read_text(encoding="utf-8")

    def test_html_list_uses_compiled_fields(self):
        content = self._snippet("html_list.txt")
        self.assertIn("entidade.campos_compilados", content)
        self.assertNotIn("entidade.campos.all", content)

    def test_generated_installer_has_no_invalid_command_and_installs_requirements(self):
        content = self._snippet("instalacao.txt")
        self.assertNotIn("Salvador:", content)
        self.assertIn("python -m pip install -r requirements.txt", content)
        self.assertIn("call .venv\\Scripts\\activate.bat", content)

    def test_postgresql_requirements_include_psycopg_binary(self):
        content = self._snippet("requirements.txt")
        self.assertIn("psycopg[binary]>=3.2,<4", content)

    def test_generation_path_is_normalized_before_rglob(self):
        normalized = GeradorService._normalizar_caminho_geracao("media/generated/1")
        self.assertIsInstance(normalized, Path)
        self.assertTrue(normalized.is_absolute())

    def test_settings_supports_validation_database_override(self):
        content = self._snippet("settings.txt")
        self.assertIn("DB_ENGINE = os.getenv", content)
        self.assertIn("django.db.backends.sqlite3", content)
        self.assertIn("AUTH_USER_MODEL = 'usuarios.User'", content)

    def test_custom_user_artifacts_exist_as_templates(self):
        self.assertIn("AbstractUser", self._snippet("custom_user_models.txt"))
        self.assertIn("UserAdmin", self._snippet("custom_user_admin.txt"))

    def test_views_use_compiled_fields_and_crud_flag(self):
        content = self._snippet("views.txt")
        self.assertIn("entidade.campos_compilados", content)
        self.assertIn("entidade.gerar_crud_views", content)
        self.assertNotIn("entidade.nome|title", content)
