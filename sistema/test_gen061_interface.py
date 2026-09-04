from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from sistema.models import Sistema
from sistema.structure_service import save_system_structure, serialize_system_structure


User = get_user_model()


class InterfaceDesignerContractTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gen061", password="senha123")

    def payload(self, **overrides):
        sistema = {
            "nome": "Sistema de Contratos",
            "descricao": "Gestão de contratos",
            "caminho": "C:/tmp/sistema_contratos",
            "tipo_menu": "lateral",
            "banco_dados": "sqlite3",
        }
        sistema.update(overrides)
        return {"sistema": sistema, "modulos": []}

    def test_model_defaults_preserve_existing_visual_contract(self):
        sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Legado",
            caminho_geracao="C:/tmp/legado",
        )
        self.assertEqual(sistema.tipo_menu, "lateral")
        self.assertEqual(sistema.interface_modo, "automatico")
        self.assertEqual(sistema.interface_densidade, "confortavel")
        self.assertEqual(sistema.interface_cor_primaria, "#0d6efd")
        self.assertEqual(sistema.interface_cor_destaque, "#6f42c1")
        self.assertTrue(sistema.interface_breadcrumb)
        self.assertTrue(sistema.interface_busca)
        self.assertTrue(sistema.interface_menu_usuario)

    def test_interface_configuration_round_trip(self):
        payload = self.payload(
            tipo_menu="superior",
            interface_modo="escuro",
            interface_densidade="compacta",
            interface_nome="Contratos HU",
            interface_cor_primaria="#112233",
            interface_cor_destaque="#aabbcc",
            interface_breadcrumb=False,
            interface_busca=False,
            interface_menu_usuario=True,
        )
        sistema = save_system_structure(user=self.user, payload=payload)
        data = serialize_system_structure(sistema)["sistema"]

        self.assertEqual(data["tipo_menu"], "superior")
        self.assertEqual(data["interface_modo"], "escuro")
        self.assertEqual(data["interface_densidade"], "compacta")
        self.assertEqual(data["interface_nome"], "Contratos HU")
        self.assertEqual(data["interface_cor_primaria"], "#112233")
        self.assertEqual(data["interface_cor_destaque"], "#aabbcc")
        self.assertFalse(data["interface_breadcrumb"])
        self.assertFalse(data["interface_busca"])
        self.assertTrue(data["interface_menu_usuario"])

    def test_legacy_payload_receives_safe_defaults(self):
        sistema = save_system_structure(user=self.user, payload=self.payload())
        data = serialize_system_structure(sistema)["sistema"]
        self.assertEqual(data["interface_modo"], "automatico")
        self.assertEqual(data["interface_densidade"], "confortavel")
        self.assertEqual(data["interface_nome"], "Sistema de Contratos")
        self.assertTrue(data["interface_breadcrumb"])
        self.assertTrue(data["interface_busca"])
        self.assertTrue(data["interface_menu_usuario"])

    def test_rejects_invalid_interface_mode(self):
        with self.assertRaisesMessage(ValidationError, "Modo da interface inválido"):
            save_system_structure(
                user=self.user,
                payload=self.payload(interface_modo="neon"),
            )

    def test_rejects_invalid_color(self):
        with self.assertRaisesMessage(ValidationError, "Cor inválida"):
            save_system_structure(
                user=self.user,
                payload=self.payload(interface_cor_primaria="azul"),
            )
