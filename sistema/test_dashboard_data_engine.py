from django.contrib.auth import get_user_model
from django.test import TestCase

from .dashboard_data_engine import DashboardDataEngine, DashboardDataError, DashboardQueryPlan
from .models import Campo, Entidade, Modulo, Sistema


class DashboardDataEngineCompileTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="data-engine-user", password="senha-forte")
        self.sistema = Sistema.objects.create(usuario=user, nome="Data Engine", caminho_geracao="/tmp/data-engine")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="vendas")
        self.cliente = Entidade.objects.create(modulo=modulo, nome="Cliente")
        Campo.objects.create(entidade=self.cliente, nome="nome", tipo="CharField", verbose_name="Nome")
        self.pedido = Entidade.objects.create(modulo=modulo, nome="Pedido")
        Campo.objects.create(entidade=self.pedido, nome="descricao", tipo="CharField")
        Campo.objects.create(entidade=self.pedido, nome="valor_total", tipo="DecimalField", max_digits=12, decimal_places=2)
        Campo.objects.create(entidade=self.pedido, nome="quantidade", tipo="IntegerField")
        Campo.objects.create(entidade=self.pedido, nome="cliente", tipo="ForeignKey", entidade_relacionada=self.cliente)

    def compile(self, config=None, entity="Pedido", widget_type="metric"):
        return DashboardDataEngine.compile(self.sistema, {
            "id": "w1",
            "type": widget_type,
            "entity": entity,
            "config": config or {},
        })

    def assert_error(self, code, config=None, entity="Pedido"):
        with self.assertRaises(DashboardDataError) as ctx:
            self.compile(config=config, entity=entity)
        self.assertEqual(ctx.exception.code, code)
        return ctx.exception

    def test_compile_returns_deterministic_query_plan(self):
        plan = self.compile({
            "operation": "sum",
            "field": "valor_total",
            "group_by": "descricao",
            "fields": ["descricao", "valor_total"],
            "ordering": "-valor_total",
            "limit": 50,
        })
        self.assertIsInstance(plan, DashboardQueryPlan)
        self.assertEqual(plan.entity, "Pedido")
        self.assertEqual(plan.operation, "sum")
        self.assertEqual(plan.value_field, "valor_total")
        self.assertEqual(plan.group_by, "descricao")
        self.assertEqual(plan.table_fields, ("descricao", "valor_total"))
        self.assertEqual(plan.ordering, "-valor_total")
        self.assertEqual(plan.limit, 50)

    def test_unknown_entity_is_rejected_before_execution(self):
        self.assert_error("entity_not_found", entity="NaoExiste")

    def test_unknown_value_field_is_rejected(self):
        self.assert_error("field_not_found", {"operation": "sum", "field": "nao_existe"})

    def test_sum_requires_numeric_field(self):
        self.assert_error("numeric_field_required", {"operation": "sum", "field": "descricao"})

    def test_avg_requires_numeric_field(self):
        self.assert_error("numeric_field_required", {"operation": "avg", "field": "descricao"})

    def test_invalid_operation_is_rejected(self):
        self.assert_error("invalid_operation", {"operation": "raw_sql", "field": "valor_total"})

    def test_arbitrary_lookup_in_grouping_is_rejected(self):
        self.assert_error("invalid_grouping", {"group_by": "cliente__nome"})

    def test_arbitrary_lookup_in_ordering_is_rejected(self):
        self.assert_error("invalid_ordering", {"ordering": "cliente__nome"})

    def test_unknown_ordering_field_is_rejected(self):
        self.assert_error("invalid_ordering", {"ordering": "-nao_existe"})

    def test_limit_must_be_inside_safe_range(self):
        self.assert_error("invalid_limit", {"limit": 501})
        self.assert_error("invalid_limit", {"limit": 0})
        self.assert_error("invalid_limit", {"limit": "muitos"})

    def test_table_fields_are_validated_and_deduplicated(self):
        plan = self.compile({"fields": ["descricao", "valor_total", "descricao"]}, widget_type="table")
        self.assertEqual(plan.table_fields, ("descricao", "valor_total"))
        self.assert_error("invalid_table_fields", {"fields": ["descricao", "cliente__nome"]})
        self.assert_error("invalid_table_fields", {"fields": ["nao_existe"]})

    def test_related_grouping_accepts_known_relation_and_label(self):
        plan = self.compile({"group_by_related": "cliente", "related_label": "nome"})
        self.assertEqual(plan.group_by_related, "cliente")
        self.assertEqual(plan.related_label, "nome")

    def test_related_grouping_rejects_non_relation(self):
        self.assert_error("invalid_related_grouping", {"group_by_related": "descricao"})

    def test_related_grouping_rejects_unknown_label(self):
        self.assert_error("invalid_related_grouping", {"group_by_related": "cliente", "related_label": "cpf"})

    def test_default_count_plan_is_safe(self):
        plan = self.compile()
        self.assertEqual(plan.operation, "count")
        self.assertEqual(plan.value_field, "id")
        self.assertEqual(plan.limit, 100)
        self.assertEqual(plan.table_fields, ())

    def test_error_has_serializable_contract(self):
        error = self.assert_error("entity_not_found", entity="NaoExiste")
        self.assertEqual(error.as_dict()["code"], "entity_not_found")
        self.assertTrue(error.as_dict()["message"])
