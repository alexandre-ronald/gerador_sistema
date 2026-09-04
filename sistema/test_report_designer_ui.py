import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ReportDesignerUITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="owner_report", password="test123")
        self.other = user_model.objects.create_user(username="other_report", password="test123")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Report App", slug="report-app")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="core")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Contrato")
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=30)
        Campo.objects.create(entidade=self.entidade, nome="fornecedor", tipo="CharField", max_length=120)
        Campo.objects.create(entidade=self.entidade, nome="valor", tipo="DecimalField", max_digits=12, decimal_places=2)
        self.url = reverse("sistema:report_designer", args=[self.sistema.id])
        self.save_url = reverse("sistema:salvar_reports", args=[self.sistema.id])
        self.client.force_login(self.user)

    def payload(self):
        return {
            "reports": {
                "Contrato": {
                    "enabled": True,
                    "title": "Relatório de contratos",
                    "description": "Acompanhe os contratos cadastrados.",
                    "fields": ["numero", "fornecedor", "valor"],
                    "filters": ["fornecedor"],
                    "order_by": "-valor",
                }
            }
        }

    def test_designer_renders_business_friendly_language(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in [
            "Design · GEN-065",
            "Relatórios",
            "Disponibilizar relatório",
            "Título do relatório",
            "Colunas do relatório",
            "Filtros para o usuário",
            "Ordenação inicial",
            "Como o relatório ficará",
            "Prévia da tabela",
            "Salvar relatórios",
        ]:
            self.assertContains(response, text)
        self.assertNotContains(response, "alert(")

    def test_save_persists_reports_and_preserves_existing_draft_keys(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"forms": {"Contrato": {}}, "workflows": {"Contrato": {}}},
        )
        response = self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertIn("forms", draft.estrutura_json)
        self.assertIn("workflows", draft.estrutura_json)
        report = draft.estrutura_json["reports"]["Contrato"]
        self.assertTrue(report["enabled"])
        self.assertEqual(report["fields"], ["numero", "fornecedor", "valor"])
        self.assertEqual(report["filters"], ["fornecedor"])
        self.assertEqual(report["order_by"], "-valor")

    def test_save_rejects_unknown_entity(self):
        payload = self.payload()
        payload["reports"]["Fantasma"] = payload["reports"].pop("Contrato")
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_save_rejects_unknown_field(self):
        payload = self.payload()
        payload["reports"]["Contrato"]["fields"].append("nao_existe")
        response = self.client.post(self.save_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("nao_existe", response.json()["mensagem"])

    def test_saved_report_is_loaded_back(self):
        self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json")
        response = self.client.get(self.url)
        self.assertContains(response, "Relatório de contratos")
        self.assertContains(response, "Acompanhe os contratos cadastrados.")

    def test_other_user_cannot_open_or_save(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(
            self.client.post(self.save_url, data=json.dumps(self.payload()), content_type="application/json").status_code,
            404,
        )
