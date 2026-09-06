import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Sistema, VersaoGeracao


class PageDesignerPreviewSelectionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="preview-selection", password="x")
        self.sistema = Sistema.objects.create(nome="Seleção Preview", usuario=self.user)
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "advanced_pages": {
                    "version": 1,
                    "pages": [
                        {
                            "id": "pagina_um",
                            "name": "Página Um",
                            "slug": "pagina-um",
                            "enabled": True,
                            "context": {"kind": "none", "entity": ""},
                            "navigation": {"visible": False, "label": "", "icon": "", "group": "", "order": 0},
                            "components": [],
                            "actions": [],
                        },
                        {
                            "id": "pagina_dois",
                            "name": "Página Dois",
                            "slug": "pagina-dois",
                            "enabled": True,
                            "context": {"kind": "none", "entity": ""},
                            "navigation": {"visible": False, "label": "", "icon": "", "group": "", "order": 0},
                            "components": [],
                            "actions": [],
                        },
                    ],
                }
            },
        )

    def test_designer_uses_contextual_wrapper_and_builds_preview_url_from_selected_page(self):
        self.client.force_login(self.user)
        url = reverse("sistema:page_designer", args=[self.sistema.pk])
        response = self.client.get(url, {"pagina": "pagina_dois"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sistema/page_designer_contextual.html")
        self.assertContains(response, "previewUrl.searchParams.set('pagina', 'advanced')")
        self.assertContains(response, "previewUrl.searchParams.set('pagina_avancada', pageId)")
        self.assertContains(response, "designerUrl.searchParams.set('pagina', pageId)")
        self.assertContains(response, "item.dataset.id")

        config = json.loads(response.context["advanced_pages_json"])
        self.assertEqual([page["id"] for page in config["pages"]], ["pagina_dois", "pagina_um"])
