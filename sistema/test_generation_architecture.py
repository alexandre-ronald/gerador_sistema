from django.contrib.auth import get_user_model
from django.test import TestCase

from sistema.models import Entidade
from sistema.structure_service import save_system_structure


User = get_user_model()


class GenerationArchitectureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="teste", password="senha123")

    def payload(self):
        return {
            "sistema": {
                "nome": "Sistema Hospitalar",
                "descricao": "Teste",
                "caminho": "C:/tmp/sistema_hospitalar",
                "tipo_menu": "lateral",
                "banco_dados": "sqlite3",
                "usar_custom_user": True,
                "gerar_api_rest": False,
                "gerar_docker": False,
                "usar_auditoria": False,
            },
            "modulos": [{
                "nome": "Gestão de Pessoas",
                "descricao": "Cadastro de pessoas",
                "entidades": [{
                    "nome": "Funcionário",
                    "nome_plural": "Funcionários",
                    "gerar_admin": True,
                    "gerar_crud_views": True,
                    "gerar_endpoints_api": False,
                    "campos": [{"nome": "Nome Completo", "tipo": "CharField", "max_length": 150}],
                }],
            }],
        }

    def test_persists_complete_editor_contract(self):
        sistema = save_system_structure(user=self.user, payload=self.payload())
        entidade = sistema.modulos.get().entidades.get()
        campo = entidade.campos.get()

        self.assertEqual(sistema.usuario, self.user)
        self.assertEqual(entidade.nome, "Funcionário")
        self.assertTrue(entidade.gerar_crud_views)
        self.assertEqual(campo.codigo_nome, "nome_completo")

    def test_crud_entity_requires_at_least_one_field(self):
        payload = self.payload()
        payload["modulos"][0]["entidades"][0]["campos"] = []
        with self.assertRaises(Exception):
            save_system_structure(user=self.user, payload=payload)

    def test_existing_entities_are_crud_enabled_after_migration_contract(self):
        self.assertTrue(Entidade._meta.get_field("gerar_crud_views").default)
