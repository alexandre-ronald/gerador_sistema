from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Entidade, Modulo, Sistema, VersaoGeracao
from .services import GeradorService


class AdvancedPagesServiceContextTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="gen0707", password="x")
        self.sistema = Sistema.objects.create(nome="Sistema GEN 0707", usuario=self.user)
        self.modulo = Modulo.objects.create(sistema=self.sistema, nome="Contratos")
        self.entidade = Entidade.objects.create(modulo=self.modulo, nome="Contrato")
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "advanced_pages": {
                    "version": 1,
                    "pages": [{
                        "id": "contratos",
                        "name": "Central de Contratos",
                        "slug": "central/contratos",
                        "enabled": True,
                        "context": {"kind": "collection", "entity": "Contrato"},
                        "navigation": {"visible": True, "label": "Contratos", "icon": "", "group": "Operação", "order": 0},
                        "components": [],
                        "actions": [],
                    }],
                }
            },
        )

    def test_prepare_context_exposes_normalized_advanced_pages(self):
        context = GeradorService(self.sistema.pk)._prepare_context()
        page = context["advanced_pages"]["pages"][0]
        self.assertEqual(page["id"], "contratos")
        self.assertEqual(page["url_name"], "advanced_page_contratos")
        self.assertEqual(page["context_app_name"], "contratos")
        self.assertEqual(page["context_model_name"], "Contrato")
        self.assertFalse(page["requires_pk"])
