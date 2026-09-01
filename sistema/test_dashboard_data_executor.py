from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from .dashboard_data_engine import DashboardDataEngine, DashboardDataError, DashboardQueryPlan


def plan(**overrides):
    values = dict(entity="Pedido", operation="count", value_field="id", group_by="", group_by_related="", related_label="__str__", table_fields=(), ordering="", limit=100)
    values.update(overrides)
    return DashboardQueryPlan(**values)


class DashboardDataExecutorTests(SimpleTestCase):
    def model(self, queryset):
        return SimpleNamespace(objects=SimpleNamespace(all=MagicMock(return_value=queryset)))

    def test_scalar_count_uses_resolved_runtime_model(self):
        qs = MagicMock()
        qs.aggregate.return_value = {"value": 7}
        result = DashboardDataEngine.execute(plan(), lambda name: self.model(qs))
        self.assertEqual(result, {"kind": "scalar", "value": 7})
        qs.aggregate.assert_called_once()

    def test_scalar_sum_returns_normalized_result(self):
        qs = MagicMock(); qs.aggregate.return_value = {"value": 125.5}
        result = DashboardDataEngine.execute(plan(operation="sum", value_field="valor_total"), lambda name: self.model(qs))
        self.assertEqual(result["kind"], "scalar")
        self.assertEqual(result["value"], 125.5)

    def test_table_selects_fields_orders_and_limits(self):
        qs = MagicMock(); ordered = MagicMock(); values = MagicMock()
        qs.order_by.return_value = ordered; ordered.values.return_value = values
        values.__getitem__.return_value = [{"descricao": "A"}]
        result = DashboardDataEngine.execute(plan(table_fields=("descricao",), ordering="-descricao", limit=10), lambda name: self.model(qs))
        self.assertEqual(result["kind"], "table")
        self.assertEqual(result["columns"], ["descricao"])
        qs.order_by.assert_called_once_with("-descricao")
        ordered.values.assert_called_once_with("descricao")
        values.__getitem__.assert_called_once_with(slice(None, 10, None))

    def test_grouped_series_uses_validated_group_field(self):
        qs = MagicMock(); grouped = MagicMock(); annotated = MagicMock()
        qs.values.return_value = grouped; grouped.annotate.return_value = annotated
        annotated.__getitem__.return_value = [{"status": "A", "value": 3}]
        result = DashboardDataEngine.execute(plan(group_by="status", limit=20), lambda name: self.model(qs))
        self.assertEqual(result["kind"], "series")
        self.assertEqual(result["group_field"], "status")
        qs.values.assert_called_once_with("status")

    def test_related_grouping_path_is_created_only_from_compiled_plan(self):
        qs = MagicMock(); grouped = MagicMock(); annotated = MagicMock()
        qs.values.return_value = grouped; grouped.annotate.return_value = annotated
        annotated.__getitem__.return_value = []
        result = DashboardDataEngine.execute(plan(group_by_related="cliente", related_label="nome"), lambda name: self.model(qs))
        self.assertEqual(result["group_field"], "cliente__nome")
        qs.values.assert_called_once_with("cliente__nome")

    def test_missing_runtime_model_has_domain_error(self):
        with self.assertRaises(DashboardDataError) as ctx:
            DashboardDataEngine.execute(plan(), lambda name: None)
        self.assertEqual(ctx.exception.code, "model_resolution_failed")

    def test_resolver_exception_is_hidden_by_domain_error(self):
        def resolver(name):
            raise RuntimeError("internal detail")
        with self.assertRaises(DashboardDataError) as ctx:
            DashboardDataEngine.execute(plan(), resolver)
        self.assertEqual(ctx.exception.code, "model_resolution_failed")
        self.assertNotIn("internal detail", ctx.exception.message)

    def test_orm_exception_is_hidden_by_domain_error(self):
        qs = MagicMock(); qs.aggregate.side_effect = RuntimeError("database detail")
        with self.assertRaises(DashboardDataError) as ctx:
            DashboardDataEngine.execute(plan(), lambda name: self.model(qs))
        self.assertEqual(ctx.exception.code, "query_execution_failed")
        self.assertNotIn("database detail", ctx.exception.message)
