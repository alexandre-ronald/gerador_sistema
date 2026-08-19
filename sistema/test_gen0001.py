from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from .models import Campo, Entidade, Modulo, Sistema
from .services import GeradorService
from .validation import class_name, technical_name, validate_specification

User = get_user_model()


class Gen0001ValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="gen0001", email="gen0001@example.com", password="secret123"
        )

    def create_system(self, **kwargs):
        return Sistema.objects.create(
            usuario=self.user,
            nome=kwargs.pop("nome", "Sistema de Teste"),
            **kwargs,
        )

    def test_technical_name_is_python_safe(self):
        self.assertEqual(technical_name("Gestão de Pessoas"), "gestao_de_pessoas")
        self.assertEqual(technical_name("123 clientes"), "_123_clientes")
        self.assertEqual(class_name("Ordem de Serviço"), "OrdemDeServico")
        self.assertEqual(class_name("Ação do Usuário"), "AcaoDoUsuario")

    def test_many_to_many_requires_related_entity(self):
        sistema = self.create_system()
        modulo = Modulo.objects.create(sistema=sistema, nome="Cadastro")
        entidade = Entidade.objects.create(modulo=modulo, nome="Cliente")
        Campo.objects.create(entidade=entidade, nome="grupos", tipo="ManyToManyField")
        with self.assertRaises(ValidationError):
            validate_specification(sistema)

    def test_decimal_requires_precision(self):
        sistema = self.create_system()
        modulo = Modulo.objects.create(sistema=sistema, nome="Financeiro")
        entidade = Entidade.objects.create(modulo=modulo, nome="Produto")
        Campo.objects.create(entidade=entidade, nome="preco", tipo="DecimalField")
        with self.assertRaises(ValidationError):
            validate_specification(sistema)

    def test_unsupported_database_is_rejected(self):
        sistema = self.create_system(banco_dados="mysql")
        with self.assertRaises(ValidationError):
            validate_specification(sistema)


class Gen0001GenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="generator", email="generator@example.com", password="secret123"
        )

    def test_generation_uses_controlled_output_path(self):
        with TemporaryDirectory() as temp_dir:
            with override_settings(GERADOR_OUTPUT_ROOT=temp_dir):
                sistema = Sistema.objects.create(
                    usuario=self.user, nome="Meu Sistema", usar_custom_user=False
                )
                modulo = Modulo.objects.create(sistema=sistema, nome="Gestão de Pessoas")
                entidade = Entidade.objects.create(modulo=modulo, nome="Pessoa")
                Campo.objects.create(
                    entidade=entidade, nome="nome completo", tipo="CharField", max_length=120
                )

                GeradorService(sistema.id).gerar_projeto_completo()

                output = Path(temp_dir) / str(self.user.id) / "meu_sistema"
                self.assertTrue((output / "meu_sistema" / "settings.py").exists())
                self.assertTrue((output / "gestao_de_pessoas" / "models.py").exists())


class Gen0001ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="views-gen0001", email="views-gen0001@example.com", password="secret123"
        )
        self.client.login(username="views-gen0001", password="secret123")

    def test_new_system_page_accepts_get(self):
        response = self.client.get("/novo/")
        self.assertEqual(response.status_code, 200)

    def test_new_system_page_creates_with_post(self):
        response = self.client.post("/novo/", {"nome": "Sistema Web", "descricao": "Teste"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Sistema.objects.filter(usuario=self.user, nome="Sistema Web").exists())
