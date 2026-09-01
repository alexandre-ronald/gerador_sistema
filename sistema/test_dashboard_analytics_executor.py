from datetime import date
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from .dashboard_analytics import DashboardAnalyticsEngine, DashboardAnalyticsPlan, DashboardFilter, DateWindow


class DashboardAnalyticsExecutorTests(SimpleTestCase):
    def plan(self, **changes):
        values = dict(date_field="criado_em", date_field_type="DateField", period="current_month", custom_start=None, custom_end=None, compare="previous_period", filters=(), current_window=DateWindow(date(2026, 9, 1), date(2026, 9, 10)), comparison_window=DateWindow(date(2026, 8, 22), date(2026, 8, 31)))
        values.update(changes)
        return DashboardAnalyticsPlan(**values)

    def test_apply_uses_validated_date_window(self):
        qs = MagicMock(); filtered = MagicMock(); qs.filter.return_value = filtered
        result = DashboardAnalyticsEngine.apply(qs, self.plan(compare="none", comparison_window=None))
        qs.filter.assert_called_once_with(criado_em__gte=date(2026, 9, 1), criado_em__lte=date(2026, 9, 10))
        self.assertIs(result, filtered)

    def test_apply_uses_comparison_window(self):
        qs = MagicMock(); filtered = MagicMock(); qs.filter.return_value = filtered
        DashboardAnalyticsEngine.apply(qs, self.plan(), comparison=True)
        qs.filter.assert_called_once_with(criado_em__gte=date(2026, 8, 22), criado_em__lte=date(2026, 8, 31))

    def test_apply_translates_eq_filter_without_arbitrary_lookup(self):
        qs = MagicMock(); after_filter = MagicMock(); after_filter.filter.return_value = MagicMock(); qs.filter.return_value = after_filter
        plan = self.plan(filters=(DashboardFilter("status", "eq", "ATIVO"),), compare="none", comparison_window=None)
        DashboardAnalyticsEngine.apply(qs, plan)
        qs.filter.assert_called_once_with(status="ATIVO")

    def test_apply_translates_neq_to_exclude(self):
        qs = MagicMock(); after_exclude = MagicMock(); after_exclude.filter.return_value = MagicMock(); qs.exclude.return_value = after_exclude
        plan = self.plan(filters=(DashboardFilter("status", "neq", "CANCELADO"),), compare="none", comparison_window=None)
        DashboardAnalyticsEngine.apply(qs, plan)
        qs.exclude.assert_called_once_with(status="CANCELADO")

    def test_apply_translates_in_operator(self):
        qs = MagicMock(); after_filter = MagicMock(); after_filter.filter.return_value = MagicMock(); qs.filter.return_value = after_filter
        plan = self.plan(filters=(DashboardFilter("status", "in", ["A", "B"]),), compare="none", comparison_window=None)
        DashboardAnalyticsEngine.apply(qs, plan)
        qs.filter.assert_called_once_with(status__in=["A", "B"])

    def test_execute_returns_current_and_comparison(self):
        qs = MagicMock(); qs.filter.side_effect = ["current_qs", "comparison_qs"]
        evaluator = MagicMock(side_effect=[120, 100])
        result = DashboardAnalyticsEngine.execute(qs, self.plan(), evaluator)
        self.assertEqual(result["current"], 120)
        self.assertEqual(result["comparison"], 100)
        self.assertEqual(result["period"], {"start": "2026-09-01", "end": "2026-09-10"})
        self.assertEqual(result["comparison_period"], {"start": "2026-08-22", "end": "2026-08-31"})

    def test_execute_without_comparison_calls_evaluator_once(self):
        qs = MagicMock(); qs.filter.return_value = "current_qs"; evaluator = MagicMock(return_value=7)
        result = DashboardAnalyticsEngine.execute(qs, self.plan(compare="none", comparison_window=None), evaluator)
        self.assertEqual(result["comparison"], None)
        evaluator.assert_called_once_with("current_qs")
