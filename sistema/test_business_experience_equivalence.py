from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase

from .advanced_page_metric_preview import enrich_related_metrics_preview
from .advanced_page_preview import build_advanced_page_preview
from .application_preview import build_preview_shell
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .services import GeradorService


class BusinessExperienceEquivalenceTests(TestCase):
    """GEN-071.9 — contrato -> Preview -> geração -> runtime relacional.

    O gate garante que relação, agregação e transporte de contexto preservam a
    mesma intenção declarativa em todas as projeções, sem uma segunda fonte de
    verdade específica para Preview ou runtime.
    """

    def setUp(self):
        user = get_user_model().objects.create_user(username="gen0719-equivalence", password="x")
        self.sistema = Sistema.objects.create(nome="Equivalência GEN 0719", usuario=user)
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Compras")
        fornecedor = Entidade.objects.create(modulo=modulo, nome="Fornecedor", gerar_crud_views=True)
        Campo.objects.create(entidade=fornecedor, nome="nome", tipo="CharField", max_length=120, verbose_name="Nome")
        contrato = Entidade.objects.create(modulo=modulo, nome="Contrato", gerar_crud_views=True)
        Campo.objects.create(entidade=contrato, nome="numero", tipo="CharField", max_length=80, verbose_name="Número")
        Campo.objects.create(entidade=contrato, nome="valor", tipo="DecimalField", max_digits=12, decimal_places=2, verbose_name="Valor")
        Campo.objects.create(
            entidade=contrato,
            nome="fornecedor",
            tipo="ForeignKey",
            entidade_relacionada=fornecedor,
            on_delete="PROTECT",
            verbose_name="Fornecedor",
        )

        relation = {"source": "page_context", "source_field": "pk", "target_field": "fornecedor"}
        self.page = {
            "id": "central_fornecedor",
            "name": "Central do Fornecedor",
            "slug": "fornecedor/central",
            "enabled": True,
            "context": {"kind": "record", "entity": "Fornecedor"},
            "navigation": {"visible": False, "label": "", "icon": "", "group": "", "order": 0},
            "components": [
                {
                    "id": "contratos_ativos",
                    "type": "metric",
                    "title": "Contratos ativos",
                    "layout": {"x": 0, "y": 0, "w": 4, "h": 1},
                    "binding": {"kind": "entity", "ref": "Contrato", "field": ""},
                    "action": "",
                    "config": {"relation": relation, "aggregate": {"operation": "count", "field": ""}},
                },
                {
                    "id": "total_contratado",
                    "type": "metric",
                    "title": "Total contratado",
                    "layout": {"x": 4, "y": 0, "w": 4, "h": 1},
                    "binding": {"kind": "entity", "ref": "Contrato", "field": ""},
                    "action": "",
                    "config": {"relation": relation, "aggregate": {"operation": "sum", "field": "valor"}},
                },
                {
                    "id": "contratos",
                    "type": "table",
                    "title": "Contratos do fornecedor",
                    "layout": {"x": 0, "y": 1, "w": 12, "h": 3},
                    "binding": {"kind": "entity", "ref": "Contrato", "field": ""},
                    "action": "",
                    "config": {"relation": relation},
                },
                {
                    "id": "novo_contrato_btn",
                    "type": "button",
                    "title": "Novo contrato",
                    "layout": {"x": 0, "y": 4, "w": 3, "h": 1},
                    "binding": {"kind": "none", "ref": "", "field": ""},
                    "action": "novo_contrato",
                    "config": {},
                },
            ],
            "actions": [{
                "id": "novo_contrato",
                "kind": "crud",
                "label": "Novo contrato",
                "target": {"entity": "Contrato", "operation": "create"},
                "transport": {"source": "page_context", "source_field": "pk", "target_field": "fornecedor"},
            }],
        }
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "advanced_pages": {"version": 1, "pages": [self.page]},
                "rbac": {"enabled": False, "roles": [], "entities": {}, "reports": {}},
            },
        )

    def test_relation_aggregate_and_transport_are_equivalent_across_projections(self):
        preview = build_preview_shell(self.sistema)
        build_advanced_page_preview(self.sistema, preview, "central_fornecedor")
        enrich_related_metrics_preview(preview)
        preview_page = preview["advanced_page"]
        preview_components = {item["id"]: item for item in preview_page["components_projection"]}

        generation = GeradorService(self.sistema.pk)._prepare_context()["advanced_pages"]
        generated_page = generation["pages"][0]
        generated_components = {item["id"]: item for item in generated_page["components"]}
        generated_actions = {item["id"]: item for item in generated_page["actions"]}

        expected_relation = self.page["components"][0]["config"]["relation"]
        self.assertEqual(preview_components["contratos_ativos"]["config"]["relation"], expected_relation)
        self.assertEqual(generated_components["contratos_ativos"]["relation_runtime"]["target_field"], expected_relation["target_field"])
        self.assertEqual(generated_components["contratos_ativos"]["relation_runtime"]["target_field_code"], "fornecedor")

        self.assertEqual(preview_components["total_contratado"]["config"]["aggregate"], {"operation": "sum", "field": "valor"})
        self.assertEqual(generated_components["total_contratado"]["aggregate_runtime"], {"operation": "sum", "field": "valor", "field_code": "valor"})
        self.assertTrue(preview_components["total_contratado"]["special"]["related_metric"])

        preview_transport = preview_page["actions_projection"]["novo_contrato"]["transport_projection"]
        generated_transport = generated_actions["novo_contrato"]["transport_runtime"]
        self.assertEqual(preview_transport["target_field"], "fornecedor")
        self.assertEqual(preview_transport["target_entity"], "Contrato")
        self.assertEqual(generated_transport["target_field"], "fornecedor")
        self.assertEqual(generated_transport["target_field_code"], "fornecedor")
        self.assertEqual(generated_transport["query_param"], "_ap_context_fornecedor")

    def test_generated_runtime_keeps_same_relation_and_transport_contract(self):
        generation = GeradorService(self.sistema.pk)._prepare_context()["advanced_pages"]
        source = render_to_string("gerador/snippets/advanced_pages_runtime.txt", {"advanced_pages": generation})
        compile(source, "advanced_pages.py", "exec")

        # O runtime emitido consome a projeção compilada, não serializa novamente
        # o contrato declarativo relation/aggregate. A equivalência declarativa é
        # coberta no teste anterior; aqui validamos os campos efetivamente usados
        # pelo código gerado.
        self.assertGreaterEqual(source.count('"relation_target_field": "fornecedor"'), 3)
        self.assertIn('"aggregate_operation": "count"', source)
        self.assertIn('"aggregate_operation": "sum"', source)
        self.assertIn('"aggregate_field": "valor"', source)
        self.assertIn('"transport_query_param": "_ap_context_fornecedor"', source)
        self.assertIn('"transport_target_field": "fornecedor"', source)
        self.assertIn('model._default_manager.filter(**{field_name: advanced_record.pk})', source)
        self.assertIn('queryset.aggregate(value=aggregate_class(field_name)).get("value")', source)
        self.assertIn("urlencode({transport_param: advanced_record.pk})", source)

    def test_record_entrypoint_and_runtime_share_same_page_identity(self):
        ctx = GeradorService(self.sistema.pk)._prepare_context()
        generated_page = ctx["advanced_pages"]["pages"][0]
        fornecedor = next(
            entity
            for module in ctx["modulos"]
            for entity in module.entidades_geracao
            if entity.nome == "Fornecedor"
        )

        self.assertEqual(generated_page["id"], "central_fornecedor")
        self.assertTrue(generated_page["requires_pk"])
        self.assertEqual(generated_page["context_entity_code"], "fornecedor")
        self.assertEqual(fornecedor.advanced_record_pages[0]["id"], generated_page["id"])
        self.assertEqual(fornecedor.advanced_record_pages[0]["url_name"], generated_page["url_name"])
