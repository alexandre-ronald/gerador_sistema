from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Sistema
from .structure_service import save_system_structure, serialize_system_structure


class Gen060StructureTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="gen060", password="teste123")

    def payload(self, modulos):
        return {
            "sistema": {
                "nome": "Sistema de Contratos",
                "descricao": "Controle de contratos e fornecedores",
                "tipo_sistema": Sistema.TIPO_CADASTRO,
                "caminho_geracao": "sistema_contratos",
                "tipo_menu": "lateral",
                "banco_dados": "sqlite3",
            },
            "modulos": modulos,
        }

    def test_area_vazia_pode_ser_salva_e_serializada(self):
        sistema = save_system_structure(
            user=self.user,
            payload=self.payload([
                {
                    "nome": "Contratos",
                    "descricao": "Gestão dos contratos e vigências",
                    "entidades": [],
                }
            ]),
        )

        area = sistema.modulos.get()
        self.assertEqual(area.nome, "Contratos")
        self.assertEqual(area.descricao, "Gestão dos contratos e vigências")
        self.assertFalse(area.entidades.exists())

        data = serialize_system_structure(sistema)
        self.assertEqual(data["modulos"][0]["nome"], "Contratos")
        self.assertEqual(data["modulos"][0]["descricao"], "Gestão dos contratos e vigências")
        self.assertEqual(data["modulos"][0]["entidades"], [])

    def test_informacao_sem_campos_pode_ser_salva(self):
        sistema = save_system_structure(
            user=self.user,
            payload=self.payload([
                {
                    "nome": "Contratos",
                    "descricao": "",
                    "entidades": [
                        {
                            "nome": "Contrato",
                            "descricao": "Dados principais do contrato",
                            "gerar_admin": True,
                            "gerar_crud_views": True,
                            "gerar_endpoints_api": False,
                            "campos": [],
                        }
                    ],
                }
            ]),
        )

        entidade = sistema.modulos.get().entidades.get()
        self.assertEqual(entidade.nome, "Contrato")
        self.assertTrue(entidade.gerar_crud_views)
        self.assertFalse(entidade.campos.exists())

    def test_area_sem_nome_e_rejeitada(self):
        with self.assertRaisesMessage(ValidationError, "Área 1: informe o nome."):
            save_system_structure(
                user=self.user,
                payload=self.payload([{"nome": "", "descricao": "", "entidades": []}]),
            )

    def test_areas_duplicadas_sao_rejeitadas_sem_diferenciar_maiusculas(self):
        with self.assertRaisesMessage(ValidationError, "Área duplicada: contratos."):
            save_system_structure(
                user=self.user,
                payload=self.payload([
                    {"nome": "Contratos", "entidades": []},
                    {"nome": "contratos", "entidades": []},
                ]),
            )

    def test_informacao_sem_nome_e_rejeitada(self):
        with self.assertRaisesMessage(
            ValidationError,
            "Informação Contratos / 1: informe o nome.",
        ):
            save_system_structure(
                user=self.user,
                payload=self.payload([
                    {
                        "nome": "Contratos",
                        "entidades": [{"nome": "", "campos": []}],
                    }
                ]),
            )

    def test_informacoes_duplicadas_na_mesma_area_sao_rejeitadas(self):
        with self.assertRaisesMessage(
            ValidationError,
            "Informação duplicada na área Contratos: contrato.",
        ):
            save_system_structure(
                user=self.user,
                payload=self.payload([
                    {
                        "nome": "Contratos",
                        "entidades": [
                            {"nome": "Contrato", "campos": []},
                            {"nome": "contrato", "campos": []},
                        ],
                    }
                ]),
            )

    def test_estrutura_antiga_com_entidade_e_campo_continua_funcionando(self):
        sistema = save_system_structure(
            user=self.user,
            payload=self.payload([
                {
                    "nome": "Fornecedores",
                    "descricao": "Cadastro de fornecedores",
                    "entidades": [
                        {
                            "nome": "Fornecedor",
                            "nome_plural": "Fornecedores",
                            "descricao": "",
                            "gerar_admin": True,
                            "gerar_crud_views": True,
                            "gerar_endpoints_api": False,
                            "campos": [
                                {
                                    "nome": "nome",
                                    "tipo": "CharField",
                                    "max_length": 150,
                                    "null": False,
                                    "blank": False,
                                    "unique": False,
                                }
                            ],
                        }
                    ],
                }
            ]),
        )

        entidade = sistema.modulos.get().entidades.get()
        campo = entidade.campos.get()
        self.assertEqual(entidade.nome, "Fornecedor")
        self.assertEqual(campo.nome, "nome")
        self.assertEqual(campo.tipo, "CharField")
        self.assertEqual(campo.max_length, 150)
