import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sistema.models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


User = get_user_model()


class PageDesignerShellTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="designer@example.com", password="secret")
        self.other = User.objects.create_user(username="other@example.com", password="secret")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Sistema Teste")
        self.modulo = Modulo.objects.create(sistema=self.sistema, nome="contratos")
        self.entidade = Entidade.objects.create(modulo=self.modulo, nome="Contrato")
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=50)
        self.client.force_login(self.user)

    def page_config(self):
        return {
            "version": 1,
            "pages": [{
                "id": "contrato_detail",
                "name": "Detalhe do Contrato",
                "slug": "contratos/detalhe",
                "enabled": True,
                "context": {"kind": "record", "entity": "Contrato"},
                "navigation": {"visible": True, "label": "Contrato", "icon": "bi-file", "group": "Contratos", "order": 10},
                "components": [],
                "actions": [],
            }],
        }

    def test_designer_requires_ownership(self):
        foreign = Sistema.objects.create(usuario=self.other, nome="Outro Sistema")
        response = self.client.get(reverse("sistema:page_designer", args=[foreign.pk]))
        self.assertEqual(response.status_code, 404)

    def test_designer_renders_shell_and_entity_metadata(self):
        response = self.client.get(reverse("sistema:page_designer", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Advanced Page Designer")
        self.assertContains(response, "GEN-070.3")
        self.assertContains(response, "Layout Engine")
        self.assertContains(response, "Canvas · 12 colunas")
        self.assertContains(response, "Contrato")
        self.assertContains(response, "Salvar páginas")

    def test_save_persists_advanced_pages_in_draft(self):
        response = self.client.post(
            reverse("sistema:salvar_page_designer", args=[self.sistema.pk]),
            data=json.dumps({"advanced_pages": self.page_config()}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertEqual(draft.estrutura_json["advanced_pages"]["pages"][0]["id"], "contrato_detail")
        self.assertEqual(draft.estrutura_json["advanced_pages"]["pages"][0]["context"]["entity"], "Contrato")

    def test_save_preserves_other_draft_contracts(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={"rbac": {"enabled": False}, "reports": {"Contrato": []}},
        )
        response = self.client.post(
            reverse("sistema:salvar_page_designer", args=[self.sistema.pk]),
            data=json.dumps({"advanced_pages": self.page_config()}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertIn("rbac", draft.estrutura_json)
        self.assertIn("reports", draft.estrutura_json)
        self.assertIn("advanced_pages", draft.estrutura_json)

    def test_save_rejects_unknown_context_entity(self):
        raw = self.page_config()
        raw["pages"][0]["context"]["entity"] = "Fantasma"
        response = self.client.post(
            reverse("sistema:salvar_page_designer", args=[self.sistema.pk]),
            data=json.dumps({"advanced_pages": raw}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "unknown_entity_reference")
        self.assertFalse(VersaoGeracao.objects.filter(sistema=self.sistema, numero=0).exists())

    def test_get_reads_existing_draft_pages(self):
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={"advanced_pages": self.page_config()},
        )
        response = self.client.get(reverse("sistema:page_designer", args=[self.sistema.pk]))
        self.assertContains(response, "contrato_detail")
        self.assertContains(response, "Detalhe do Contrato")
