from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sistema.advanced_page_preview import build_advanced_page_preview
from sistema.application_preview import build_preview_shell
from sistema.models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


User = get_user_model()


class AdvancedPagePreviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="advanced-preview@example.com", password="secret")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Preview Avançado")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Contratos")
        self.entidade = Entidade.objects.create(modulo=modulo, nome="Contrato", gerar_crud_views=True)
        Campo.objects.create(entidade=self.entidade, nome="numero", tipo="CharField", max_length=80, verbose_name="Número")
        Campo.objects.create(entidade=self.entidade, nome="status", tipo="CharField", max_length=40, verbose_name="Status")
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "advanced_pages": {
                    "version": 1,
                    "pages": [
                        {
                            "id": "central_contratos",
                            "name": "Central de Contratos",
                            "slug": "central/contratos",
                            "enabled": True,
                            "context": {"kind": "collection", "entity": "Contrato"},
                            "navigation": {"visible": True, "label": "Central", "icon": "bi-window", "group": "Operação", "order": 1},
                            "components": [
                                {"id": "titulo", "type": "title", "title": "Central", "layout": {"x": 0, "y": 0, "w": 12, "h": 1}, "binding": {"kind": "none", "ref": "", "field": ""}, "action": "", "config": {}},
                                {"id": "tabela", "type": "table", "title": "Contratos", "layout": {"x": 0, "y": 1, "w": 12, "h": 3}, "binding": {"kind": "entity", "ref": "Contrato", "field": ""}, "action": "", "config": {}},
                            ],
                            "actions": [],
                        }
                    ],
                },
                "rbac": {"enabled": False, "roles": [], "entities": {}, "reports": {}},
            },
        )

    def test_projection_uses_persisted_advanced_page_contract(self):
        preview = build_preview_shell(self.sistema)
        build_advanced_page_preview(self.sistema, preview, "central_contratos")
        page = preview["advanced_page"]
        self.assertEqual(preview["page_kind"], "advanced")
        self.assertEqual(page["id"], "central_contratos")
        self.assertEqual(page["components_projection"][1]["type"], "table")
        self.assertEqual(len(page["components_projection"][1]["demo_rows"]), 4)
        self.assertEqual([item["id"] for item in preview["advanced_pages"]], ["central_contratos"])

    def test_preview_view_renders_advanced_shell_and_designer_roundtrip_link(self):
        self.client.force_login(self.user)
        url = reverse("sistema:application_preview", args=[self.sistema.pk])
        response = self.client.get(url, {"pagina": "advanced", "pagina_avancada": "central_contratos"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sistema/application_preview_advanced.html")
        self.assertContains(response, 'data-preview-page="advanced"')
        self.assertContains(response, 'data-advanced-page-id="central_contratos"')
        self.assertContains(response, 'data-preview-designer="advanced"')
        self.assertContains(response, "Central de Contratos")

    def test_invalid_role_hides_collection_page_fail_closed(self):
        preview = build_preview_shell(self.sistema, selected_role_id="papel-inexistente")
        build_advanced_page_preview(self.sistema, preview, "central_contratos")
        self.assertFalse(preview["advanced_page"]["allowed"])
        self.assertEqual(preview["advanced_pages"], [])
