from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .validation_center import ValidationCenterService, validate_system


class ValidationCenterTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="validation-owner", password="senha-forte")
        self.other = User.objects.create_user(username="validation-other", password="senha-forte")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Validation Center Teste")
        self.client.force_login(self.user)

    def _create_valid_definition(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="cadastro")
        entidade = Entidade.objects.create(modulo=modulo, nome="Pessoa")
        Campo.objects.create(entidade=entidade, nome="nome", tipo="CharField", max_length=120)
        return modulo, entidade

    def test_report_has_stable_contract(self):
        report = validate_system(self.sistema)
        self.assertEqual(report["system"]["id"], self.sistema.pk)
        self.assertIn(report["overall_status"], ValidationCenterService.STATUSES)
        self.assertEqual(report["total"], len(report["checks"]))
        self.assertEqual(report["total"], report["successes"] + report["warnings"] + report["errors"] + report["pending"])
        for check in report["checks"]:
            self.assertEqual(set(check), {"key", "label", "status", "summary", "details"})

    def test_valid_definition_produces_structured_success(self):
        self._create_valid_definition()
        report = validate_system(self.sistema)
        definition = next(check for check in report["checks"] if check["key"] == "definition")
        self.assertEqual(definition["status"], "success")

    def test_critical_relationship_error_blocks_release(self):
        _, entidade = self._create_valid_definition()
        Campo.objects.create(entidade=entidade, nome="gestor", tipo="ForeignKey", entidade_relacionada=None)
        report = validate_system(self.sistema)
        relationships = next(check for check in report["checks"] if check["key"] == "relationships")
        self.assertEqual(relationships["status"], "error")
        self.assertEqual(report["overall_status"], "error")
        self.assertFalse(report["release_ready"])

    def test_warning_is_not_counted_as_error(self):
        report = validate_system(self.sistema)
        self.assertGreater(report["warnings"], 0)
        self.assertEqual(report["errors"], 0)

    def test_dashboard_is_part_of_report(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"dashboard": {"enabled": True, "widgets": [{"type": "metric", "x": 0, "y": 0, "w": 4, "h": 3}]}},
        )
        report = validate_system(self.sistema)
        dashboard = next(check for check in report["checks"] if check["key"] == "dashboard")
        self.assertEqual(dashboard["status"], "success")

    def test_dashboard_outside_grid_is_error(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"dashboard": {"enabled": True, "widgets": [{"type": "metric", "x": 10, "y": 0, "w": 4, "h": 3}]}},
        )
        report = validate_system(self.sistema)
        dashboard = next(check for check in report["checks"] if check["key"] == "dashboard")
        self.assertEqual(dashboard["status"], "error")
        self.assertFalse(report["release_ready"])

    def test_validation_center_requires_owner(self):
        response = self.client.get(reverse("sistema:validation_center", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Validation Center")
        self.client.force_login(self.other)
        response = self.client.get(reverse("sistema:validation_center", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 404)

    def test_validation_center_does_not_modify_system(self):
        self._create_valid_definition()
        before = {
            "systems": Sistema.objects.count(),
            "modules": Modulo.objects.count(),
            "entities": Entidade.objects.count(),
            "fields": Campo.objects.count(),
            "versions": VersaoGeracao.objects.count(),
        }
        response = self.client.get(reverse("sistema:validation_center", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        after = {
            "systems": Sistema.objects.count(),
            "modules": Modulo.objects.count(),
            "entities": Entidade.objects.count(),
            "fields": Campo.objects.count(),
            "versions": VersaoGeracao.objects.count(),
        }
        self.assertEqual(before, after)
