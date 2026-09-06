from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Sistema, VersaoGeracao


class AdvancedPagePreviewEntryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="preview-entry", password="x")
        self.sistema = Sistema.objects.create(nome="Preview Entry", usuario=self.user)
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "advanced_pages": {
                    "version": 1,
                    "pages": [{
                        "id": "pagina_operacional",
                        "name": "Página Operacional",
                        "slug": "pagina-operacional",
                        "enabled": True,
                        "context": {"kind": "none", "entity": ""},
                        "navigation": {"visible": True, "label": "Operacional", "icon": "", "group": "Páginas", "order": 0},
                        "components": [],
                        "actions": [],
                    }],
                },
                "rbac": {"enabled": False, "roles": [], "entities": {}, "reports": {}},
            },
        )

    def test_base_preview_link_from_page_designer_opens_first_enabled_advanced_page(self):
        self.client.force_login(self.user)
        designer_url = reverse("sistema:page_designer", args=[self.sistema.pk])
        preview_url = reverse("sistema:application_preview", args=[self.sistema.pk])

        response = self.client.get(
            preview_url,
            HTTP_REFERER=f"http://testserver{designer_url}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sistema/application_preview_advanced.html")
        self.assertEqual(response.context["preview"]["page_kind"], "advanced")
        self.assertEqual(response.context["preview"]["advanced_page"]["id"], "pagina_operacional")
        self.assertContains(response, "Página Operacional")
