from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from .dashboard_analytics import DashboardAnalyticsEngine, DashboardAnalyticsError
from .models import Campo, Entidade, Modulo, Sistema


class DashboardAnalyticsTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="analytics-user", password="senha-forte")
        self.sistema = Sistema.objects.create(usuario=user, nome="Analytics")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="vendas")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Pedido")
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField")
        Campo.objects.create(entidade=self.entidade, nome="valor_total", tipo="DecimalField", max_digits=12, decimal_places=2)
        Campo.objects.create(entidade=self.entidade, nome="data_pedido", tipo="DateField")
        Campo.objects.create(entidade=self.entidade, nome="criado_em", tipo="DateTimeField")

    def widget(self, analytics=None):
        config = {"operation": "sum", "field": "valor_total"}
        if analytics is not None:
            config["analytics"] = analytics
        return {"type": "metric", "entity": "Pedido", "config": config, "x": 8, "y": 3, "w": 4, "h": 2}

    def test_legacy_widget_compiles_to_no_temporal_filter(self):
        plan = DashboardAnalyticsEngine.compile(self.sistema, self.widget(), reference_date=date(2026, 9, 1))
        self.assertEqual(plan.period, "all")
        self.assertEqual(plan.compare, "none")
        self.assertIsNone(plan.current_window)
        self.assertEqual(plan.filters, ())

    def test_current_month_and_previous_period_are_deterministic(self):
        plan = DashboardAnalyticsEngine.compile(self.sistema, self.widget({"date_field": "data_pedido", "period": "current_month", "compare": "previous_period"}), reference_date=date(2026, 9, 15))
        self.assertEqual(plan.current_window.start, date(2026, 9, 1))
        self.assertEqual(plan.current_window.end, date(2026, 9, 15))
        self.assertEqual(plan.comparison_window.start, date(2026, 8, 17))
        self.assertEqual(plan.comparison_window.end, date(2026, 8, 31))

    def test_previous_year_handles_leap_day(self):
        plan = DashboardAnalyticsEngine.compile(self.sistema, self.widget({"date_field": "data_pedido", "period": "today", "compare": "previous_year"}), reference_date=date(2024, 2, 29))
        self.assertEqual(plan.comparison_window.start, date(2023, 2, 28))
        self.assertEqual(plan.comparison_window.end, date(2023, 2, 28))

    def test_custom_period_parses_iso_dates(self):
        plan = DashboardAnalyticsEngine.compile(self.sistema, self.widget({"date_field": "data_pedido", "period": "custom", "custom_start": "2026-08-01", "custom_end": "2026-08-31"}), reference_date=date(2026, 9, 1))
        self.assertEqual(plan.current_window.start, date(2026, 8, 1))
        self.assertEqual(plan.current_window.end, date(2026, 8, 31))

    def test_custom_period_rejects_inverted_dates(self):
        with self.assertRaises(DashboardAnalyticsError) as ctx:
            DashboardAnalyticsEngine.compile(self.sistema, self.widget({"date_field": "data_pedido", "period": "custom", "custom_start": "2026-09-10", "custom_end": "2026-09-01"}))
        self.assertEqual(ctx.exception.code, "invalid_custom_period")

    def test_temporal_period_requires_date_field(self):
        with self.assertRaises(DashboardAnalyticsError) as ctx:
            DashboardAnalyticsEngine.compile(self.sistema, self.widget({"period": "last_30_days"}))
        self.assertEqual(ctx.exception.code, "invalid_date_field")

    def test_unknown_and_lookup_filter_fields_are_rejected(self):
        for field in ("nao_existe", "status__icontains"):
            with self.subTest(field=field):
                with self.assertRaises(DashboardAnalyticsError) as ctx:
                    DashboardAnalyticsEngine.compile(self.sistema, self.widget({"filters": [{"field": field, "operator": "eq", "value": "A"}]}))
                self.assertEqual(ctx.exception.code, "invalid_filter_field")

    def test_text_filter_operator_is_type_checked(self):
        plan = DashboardAnalyticsEngine.compile(self.sistema, self.widget({"filters": [{"field": "status", "operator": "icontains", "value": "aprov"}]}))
        self.assertEqual(plan.filters[0].operator, "icontains")
        with self.assertRaises(DashboardAnalyticsError) as ctx:
            DashboardAnalyticsEngine.compile(self.sistema, self.widget({"filters": [{"field": "valor_total", "operator": "icontains", "value": "10"}]}))
        self.assertEqual(ctx.exception.code, "invalid_filter_operator")

    def test_in_and_isnull_validate_value_shape(self):
        with self.assertRaises(DashboardAnalyticsError) as ctx:
            DashboardAnalyticsEngine.compile(self.sistema, self.widget({"filters": [{"field": "status", "operator": "in", "value": "A"}]}))
        self.assertEqual(ctx.exception.code, "invalid_filter_value")
        with self.assertRaises(DashboardAnalyticsError) as ctx:
            DashboardAnalyticsEngine.compile(self.sistema, self.widget({"filters": [{"field": "status", "operator": "isnull", "value": "true"}]}))
        self.assertEqual(ctx.exception.code, "invalid_filter_value")

    def test_comparison_is_not_allowed_for_all_period(self):
        with self.assertRaises(DashboardAnalyticsError) as ctx:
            DashboardAnalyticsEngine.compile(self.sistema, self.widget({"compare": "previous_period"}))
        self.assertEqual(ctx.exception.code, "invalid_comparison")
