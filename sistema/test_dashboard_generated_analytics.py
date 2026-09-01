from django.template.loader import render_to_string
from django.test import SimpleTestCase


class GeneratedDashboardAnalyticsTests(SimpleTestCase):
    def source(self):
        return render_to_string('gerador/snippets/dashboard_data_views.txt', {'dashboard_json': '[]'})

    def test_runtime_supports_periods_and_comparisons(self):
        source=self.source()
        self.assertIn("'last_30_days'",source)
        self.assertIn("'custom'",source)
        self.assertIn("'previous_period'",source)
        self.assertIn("'previous_year'",source)
        self.assertIn("comparison_window=_previous",source)

    def test_runtime_applies_current_and_comparison_querysets(self):
        source=self.source()
        self.assertIn("current_qs=_analytics_qs",source)
        self.assertIn("previous_qs=_analytics_qs",source)
        self.assertIn("item['comparison']=_evaluate",source)

    def test_runtime_supports_safe_filters(self):
        source=self.source()
        self.assertIn("if operator == 'neq': qs=qs.exclude",source)
        self.assertIn("lookup=FILTER_LOOKUPS.get(operator)",source)
        self.assertIn("if not _field(model, name): raise ValueError('Filtro inválido')",source)

    def test_runtime_supports_date_and_datetime_windows(self):
        source=self.source()
        self.assertIn("isinstance(field, (models.DateField, models.DateTimeField))",source)
        self.assertIn("f'{name}__gte'",source)
        self.assertIn("f'{name}__lt'",source)
        self.assertIn("f'{name}__lte'",source)

    def test_runtime_response_exposes_analytics_metadata(self):
        source=self.source()
        self.assertIn("'comparison':None",source)
        self.assertIn("'period':None",source)
        self.assertIn("'comparison_period':None",source)

    def test_runtime_keeps_widget_local_error_isolation(self):
        source=self.source()
        self.assertIn("except Exception: item['error']='Não foi possível executar a consulta deste widget.'",source)
        self.assertIn("result.append(item)",source)
