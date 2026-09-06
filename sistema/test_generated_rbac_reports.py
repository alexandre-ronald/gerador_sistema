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
                "reports": {
                    "Contrato": [
                        {
                            "id": "geral",
                            "enabled": True,
                            "title": "Relatório Geral",
                            "fields": [],
                            "filters": [],
                            "navigation": {"path": ["Contratos"], "label": "Relatório Geral"},
                        }
                    ]
                },
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

    def advanced_pages(self):
        return {
            "pages": [
                {
                    "id": "inicio_operacional",
                    "name": "Início Operacional",
                    "url_name": "advanced_page_inicio_operacional",
                    "requires_pk": False,
                    "context": {"kind": "none", "entity": ""},
                    "context_app_name": "",
                    "context_model_name": "",
                    "navigation": {"visible": True, "label": "Operação", "group": "Operacional", "order": 1},
                },
                {
                    "id": "central_contratos",
                    "name": "Central de Contratos",
                    "url_name": "advanced_page_central_contratos",
                    "requires_pk": False,
                    "context": {"kind": "collection", "entity": "Contrato"},
                    "context_app_name": "contratos",
                    "context_model_name": "Contrato",
                    "navigation": {"visible": True, "label": "Central", "group": "Contratos", "order": 2},
                },
                {
                    "id": "contrato_detail",
                    "name": "Detalhe do Contrato",
                    "url_name": "advanced_page_contrato_detail",
                    "requires_pk": True,
                    "context": {"kind": "record", "entity": "Contrato"},
                    "context_app_name": "contratos",
                    "context_model_name": "Contrato",
                    "navigation": {"visible": True, "label": "Detalhe", "group": "Contratos", "order": 3},
                },
            ]
        }

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
                "advanced_pages": self.advanced_pages(),
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

    def test_generated_navigation_includes_safe_advanced_pages(self):
        self.modulo.app_name = "contratos"
        self.modulo.entidades_geracao = [self.entidade]
        self.entidade.codigo_nome = "contrato"
        self.entidade.classe_nome = "Contrato"

        source = render_to_string(
            "gerador/snippets/navigation_context.txt",
            {
                "modulos": [self.modulo],
                "notifications": {"enabled": False},
                "advanced_pages": self.advanced_pages(),
            },
        )

        compile(source, "<generated-navigation-advanced>", "exec")
        self.assertIn('"label": "Operação"', source)
        self.assertIn('"advanced_page_id": "inicio_operacional"', source)
        self.assertIn('"advanced_page_id": "central_contratos"', source)
        self.assertIn('"advanced_context_kind": "collection"', source)
        self.assertNotIn('"advanced_page_id": "contrato_detail"', source)
        self.assertIn('item.get("is_advanced_page") and item.get("advanced_context_kind") == "none"', source)
        self.assertIn("current_url_name in active_names", source)
