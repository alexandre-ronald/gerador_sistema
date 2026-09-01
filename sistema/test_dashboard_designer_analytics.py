from django.template.loader import render_to_string
from django.test import SimpleTestCase


class DashboardDesignerAnalyticsTests(SimpleTestCase):
    def source(self):
        return render_to_string(
            'sistema/dashboard_builder.html',
            {
                'sistema': type('S', (), {'id': 1})(),
                'config': {'title': 'Dashboard'},
                'config_json': '{"widgets":[]}',
                'entity_metadata_json': '{}',
                'entities': [],
                'widget_types': [('metric', 'Indicador', 'bi bi-123')],
                'csrf_token': 'token',
            },
        )

    def test_designer_exposes_temporal_analytics_controls(self):
        source = self.source()
        self.assertIn('Análise temporal', source)
        self.assertIn('Campo de data', source)
        self.assertIn('Período', source)
        self.assertIn('Comparação', source)
        self.assertIn('Adicionar filtro', source)
        self.assertIn("data-an=\"date_field\"", source)
        self.assertIn("data-an=\"period\"", source)
        self.assertIn("data-an=\"compare\"", source)

    def test_designer_keeps_relationship_and_table_controls(self):
        source = self.source()
        self.assertIn('Campo relacionado', source)
        self.assertIn('Rótulo relacionado', source)
        self.assertIn('Campos da tabela', source)
        self.assertIn('data-q=\"group_by_related\"', source)
        self.assertIn('data-q=\"related_label\"', source)
        self.assertIn('data-table-field=', source)

    def test_new_widget_has_backward_compatible_analytics_defaults(self):
        source = self.source()
        self.assertIn("analytics:{date_field:'',period:'all',custom_start:'',custom_end:'',compare:'none',filters:[]}", source)
        self.assertIn('normalizeAnalytics(w.config)', source)

    def test_custom_period_controls_are_supported(self):
        source = self.source()
        self.assertIn("an.period==='custom'", source)
        self.assertIn('data-an=\"custom_start\"', source)
        self.assertIn('data-an=\"custom_end\"', source)

    def test_filter_editor_supports_safe_operator_contract(self):
        source = self.source()
        for operator in ('eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'contains', 'icontains', 'in', 'isnull'):
            self.assertIn("'%s'" % operator, source)
        self.assertIn('data-filter-field=', source)
        self.assertIn('data-filter-operator=', source)
        self.assertIn('data-filter-value=', source)
        self.assertIn('data-remove-filter=', source)

    def test_preview_and_grid_contract_remain_present(self):
        source = self.source()
        self.assertIn("draggable=\"${previewMode?'false':'true'}\"", source)
        self.assertIn('function reflow(priority=null)', source)
        self.assertIn('x+w.w<=12', source)
        self.assertIn('function setPreview(enabled)', source)
