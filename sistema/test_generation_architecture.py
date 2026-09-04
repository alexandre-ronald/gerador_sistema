from django.contrib.auth import get_user_model
from django.test import TestCase

from sistema.models import Entidade
from sistema.structure_service import save_system_structure, serialize_system_structure


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
                "gerar_api_rest": True,
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
                    "gerar_endpoints_api": True,
                    "campos": [{
                        "nome": "Nome Completo",
                        "tipo": "CharField",
                        "max_length": 150,
                        "verbose_name": "Nome completo",
                        "help_text": "Informe o nome completo.",
                        "default_value": "",
                        "null": False,
                        "blank": False,
                        "unique": False,
                    }],
                }],
            }],
        }

    def test_persists_complete_editor_contract(self):
        sistema = save_system_structure(user=self.user, payload=self.payload())
        entidade = sistema.modulos.get().entidades.get()
        campo = entidade.campos.get()

        self.assertEqual(sistema.usuario, self.user)
        self.assertTrue(sistema.usar_custom_user)
        self.assertTrue(sistema.gerar_api_rest)
        self.assertEqual(entidade.nome, "Funcionário")
        self.assertTrue(entidade.gerar_crud_views)
        self.assertTrue(entidade.gerar_endpoints_api)
        self.assertEqual(campo.codigo_nome, "nome_completo")
        self.assertEqual(campo.verbose_name, "Nome completo")
        self.assertEqual(campo.help_text, "Informe o nome completo.")

    def test_edit_preserves_api_flags_when_payload_is_true(self):
        sistema = save_system_structure(user=self.user, payload=self.payload())
        payload = self.payload()
        payload["sistema"]["descricao"] = "Editado"
        updated = save_system_structure(user=self.user, payload=payload, sistema_id=sistema.id)
        entidade = updated.modulos.get().entidades.get()
        self.assertTrue(updated.gerar_api_rest)
        self.assertTrue(updated.usar_custom_user)
        self.assertTrue(entidade.gerar_endpoints_api)

    def test_advanced_field_metadata_round_trip(self):
        payload = self.payload()
        payload["modulos"][0]["entidades"].append({
            "nome": "Setor",
            "nome_plural": "Setores",
            "gerar_admin": True,
            "gerar_crud_views": True,
            "gerar_endpoints_api": False,
            "campos": [{"nome": "nome", "tipo": "CharField", "max_length": 100}],
        })
        payload["modulos"][0]["entidades"][0]["campos"].append({
            "nome": "setor",
            "tipo": "ForeignKey",
            "rel": "Setor",
            "on_delete": "models.PROTECT",
            "related_name": "funcionarios",
            "verbose_name": "Setor de lotação",
            "help_text": "Selecione o setor.",
            "null": True,
            "blank": True,
            "unique": False,
        })
        sistema = save_system_structure(user=self.user, payload=payload)
        serialized = serialize_system_structure(sistema)
        funcionario = serialized["modulos"][0]["entidades"][0]
        rel = next(field for field in funcionario["campos"] if field["nome"] == "setor")
        self.assertEqual(rel["rel"], "Setor")
        self.assertEqual(rel["on_delete"], "models.PROTECT")
        self.assertEqual(rel["related_name"], "funcionarios")
        self.assertEqual(rel["verbose_name"], "Setor de lotação")
        self.assertEqual(rel["help_text"], "Selecione o setor.")
        self.assertTrue(rel["null"])
        self.assertTrue(rel["blank"])

    def test_crud_entity_may_be_created_before_fields_are_defined(self):
        payload = self.payload()
        payload["modulos"][0]["entidades"][0]["campos"] = []
        sistema = save_system_structure(user=self.user, payload=payload)
        entidade = sistema.modulos.get().entidades.get()
        self.assertTrue(entidade.gerar_crud_views)
        self.assertEqual(entidade.campos.count(), 0)

    def test_existing_entities_are_crud_enabled_after_migration_contract(self):
        self.assertTrue(Entidade._meta.get_field("gerar_crud_views").default)
