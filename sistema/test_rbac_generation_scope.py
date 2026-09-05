from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Entidade, Modulo, Sistema, VersaoGeracao
from .templatetags.rbac_generation import _config


class RBACGenerationScopeTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="rbac_scope", password="test123")
        self.sistema = Sistema.objects.create(usuario=user, nome="Sistema multi módulo")
        modulo_a = Modulo.objects.create(sistema=self.sistema, nome="Contratos")
        modulo_b = Modulo.objects.create(sistema=self.sistema, nome="Fornecedores")
        self.contrato = Entidade.objects.create(modulo=modulo_a, nome="Contrato")
        self.fornecedor = Entidade.objects.create(modulo=modulo_b, nome="Fornecedor")
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "rbac": {
                    "enabled": True,
                    "roles": [
                        {
                            "id": "gestor",
                            "label": "Gestor",
                            "description": "",
                            "group": "Gestores",
                            "order": 0,
                        }
                    ],
                    "entities": {
                        "Contrato": {
                            "roles": {"gestor": ["list", "view"]},
                            "transitions": {},
                        },
                        "Fornecedor": {
                            "roles": {"gestor": ["list"]},
                            "transitions": {},
                        },
                    },
                }
            },
        )

    def test_module_projection_validates_against_whole_system_then_filters(self):
        config = _config([self.contrato])
        self.assertTrue(config["enabled"])
        self.assertEqual([role["id"] for role in config["roles"]], ["gestor"])
        self.assertEqual(set(config["entities"]), {"Contrato"})
        self.assertEqual(config["entities"]["Contrato"]["roles"]["gestor"], ["list", "view"])

    def test_other_module_policy_does_not_raise_unknown_entity(self):
        config = _config([self.fornecedor])
        self.assertEqual(set(config["entities"]), {"Fornecedor"})
        self.assertEqual(config["entities"]["Fornecedor"]["roles"]["gestor"], ["list"])
