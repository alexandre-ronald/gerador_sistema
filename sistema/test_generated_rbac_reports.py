from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase

from sistema.models import Entidade, Modulo, Sistema, VersaoGeracao
from sistema.templatetags.rbac_generation import rbac_generation_config


User = get_user_model()


class _Groups:
    def __init__(self, *names):
        self.names = names

    def values_list(self, *args, **kwargs):
        return self.names


class GeneratedRBACReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="rbac-report@example.com", password="secret")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Sistema RBAC")
        self.modulo = Modulo.objects.create(sistema=self.sistema, nome="contratos")
        self.entidade = Entidade.objects.create(modulo=self.modulo, nome="Contrato", gerar_crud_views=True)
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "reports": {"Contrato": [{"id": "geral", "name": "Relatório Geral"}]},
                "rbac": {
                    "enabled": True,
                    "roles": [
                        {"id": "gestor", "label": "Gestor", "group": "Gestores", "order": 0},
                        {"id": "leitor", "label": "Leitor", "group": "Leitores", "order": 1},
                    ],
                    "entities": {
                        "Contrato": {
                            "roles": {"gestor": ["list", "view"], "leitor": ["view"]},
                            "transitions": {},
                        }
                    },
                    "reports": {"Contrato": {"geral": ["gestor"]}},
                },
            },
        )

    def test_generation_projection_keeps_report_policy(self):
        config = rbac_generation_config([self.entidade])
        self.assertTrue(config["enabled"])
        self.assertEqual(config["reports"]["Contrato"]["geral"], ["gestor"])

    def test_generated_runtime_fails_closed_for_report(self):
        source = render_to_string(
            "gerador/snippets/rbac_runtime.txt",
            {"entidades": [self.entidade]},
        )
        namespace = {}
        exec(source, namespace)

        gestor = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            groups=_Groups("Gestores"),
        )
        leitor = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            groups=_Groups("Leitores"),
        )

        self.assertTrue(namespace["can_report"](gestor, "Contrato", "geral"))
        self.assertFalse(namespace["can_report"](leitor, "Contrato", "geral"))
        self.assertFalse(namespace["can_report"](gestor, "Contrato", "inexistente"))
        self.assertIn("protected_report_view", namespace)

    def test_generated_navigation_uses_same_rbac_contract(self):
        self.modulo.app_name = "contratos"
        self.modulo.entidades_geracao = [self.entidade]
        self.entidade.codigo_nome = "contrato"
        self.entidade.classe_nome = "Contrato"

        source = render_to_string(
            "gerador/snippets/navigation_context.txt",
            {
                "modulos": [self.modulo],
                "notifications": {"enabled": False},
            },
        )

        compile(source, "<generated-navigation>", "exec")
        self.assertIn('"entity_name": "Contrato"', source)
        self.assertIn('"rbac_action": "list"', source)
        self.assertIn('"report_id": "geral"', source)
        self.assertIn("def _rbac_item_allowed", source)
        self.assertIn("rbac.has_entity_action", source)
        self.assertIn("rbac.can_report", source)
        self.assertIn("except Exception:\n        return False", source)
