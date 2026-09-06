from django.test import SimpleTestCase

from .advanced_page_metric_preview import enrich_related_metrics_preview
from .advanced_pages import AdvancedPageContractError
from .advanced_pages_semantics import validate_advanced_pages_semantics


class RelatedMetricTests(SimpleTestCase):
    def _entities(self):
        return [
            {"name": "Fornecedor", "fields": [{"name": "nome", "type": "CharField", "related_entity": ""}]},
            {
                "name": "Contrato",
                "fields": [
                    {"name": "fornecedor", "type": "ForeignKey", "related_entity": "Fornecedor"},
                    {"name": "valor", "type": "DecimalField", "related_entity": ""},
                    {"name": "numero", "type": "CharField", "related_entity": ""},
                ],
            },
        ]

    def _config(self, operation="count", field=""):
        return {
            "version": 1,
            "pages": [{
                "id": "central_fornecedor", "name": "Central do Fornecedor", "slug": "fornecedor/central", "enabled": True,
                "context": {"kind": "record", "entity": "Fornecedor"},
                "navigation": {"visible": False, "label": "", "icon": "", "group": "", "order": 0},
                "components": [{
                    "id": "total_contratos", "type": "metric", "title": "Contratos ativos",
                    "layout": {"x": 0, "y": 0, "w": 4, "h": 1},
                    "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "",
                    "config": {
                        "relation": {"source": "page_context", "source_field": "pk", "target_field": "fornecedor"},
                        "aggregate": {"operation": operation, "field": field},
                    },
                }],
                "actions": [],
            }],
        }

    def test_count_metric_is_normalized_without_field(self):
        config = validate_advanced_pages_semantics(self._config("count", "valor"), entities_metadata=self._entities())
        aggregate = config["pages"][0]["components"][0]["config"]["aggregate"]
        self.assertEqual(aggregate, {"operation": "count", "field": ""})

    def test_sum_accepts_numeric_field(self):
        config = validate_advanced_pages_semantics(self._config("sum", "valor"), entities_metadata=self._entities())
        self.assertEqual(config["pages"][0]["components"][0]["config"]["aggregate"]["field"], "valor")

    def test_sum_rejects_text_field(self):
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(self._config("sum", "numero"), entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "incompatible_aggregate_field")

    def test_rejects_unknown_operation(self):
        with self.assertRaises(AdvancedPageContractError) as ctx:
            validate_advanced_pages_semantics(self._config("median", "valor"), entities_metadata=self._entities())
        self.assertEqual(ctx.exception.code, "unknown_aggregate_operation")

    def test_preview_enriches_related_metric(self):
        preview = {"advanced_page": {"components_projection": [{
            "id": "total_contratos", "type": "metric", "binding": {"ref": "Contrato"},
            "config": {"relation": {"target_field": "fornecedor"}, "aggregate": {"operation": "count", "field": ""}},
            "special": {}, "demo_value": None,
        }]}}
        enrich_related_metrics_preview(preview)
        metric = preview["advanced_page"]["components_projection"][0]
        self.assertEqual(metric["demo_value"], "7")
        self.assertTrue(metric["special"]["related_metric"])
        self.assertEqual(metric["special"]["relation_summary"], "Contrato.fornecedor = contexto.pk")
