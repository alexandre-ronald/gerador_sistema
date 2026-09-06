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

    def test_workflow_action_projects_confirmation_contract(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        structure = draft.estrutura_json
        page = structure["advanced_pages"]["pages"][0]
        page["context"] = {"kind": "record", "entity": "Contrato"}
        page["components"].append({
            "id": "aprovar",
            "type": "workflow_action",
            "title": "Aprovar",
            "layout": {"x": 0, "y": 4, "w": 4, "h": 1},
            "binding": {"kind": "workflow", "ref": "Contrato", "field": ""},
            "action": "aprovar_contrato",
            "config": {},
        })
        page["actions"] = [{
            "id": "aprovar_contrato",
            "kind": "workflow",
            "label": "Aprovar contrato",
            "target": {"entity": "Contrato", "transition": "aprovar"},
        }]
        structure["workflows"] = {
            "Contrato": {
                "enabled": True,
                "transitions": [{
                    "id": "aprovar",
                    "label": "Aprovar",
                    "confirm": True,
                    "confirm_message": "Confirmar aprovação do contrato?",
                }],
            }
        }
        draft.estrutura_json = structure
        draft.save(update_fields=["estrutura_json"])
        preview = build_preview_shell(self.sistema)
        build_advanced_page_preview(self.sistema, preview, "central_contratos")
        action = preview["advanced_page"]["actions_projection"]["aprovar_contrato"]
        self.assertTrue(action["confirm"])
        self.assertEqual(action["confirm_message"], "Confirmar aprovação do contrato?")

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

    def test_advanced_navigation_marks_selected_page_and_exposes_contextual_link(self):
        self.client.force_login(self.user)
        url = reverse("sistema:application_preview", args=[self.sistema.pk])
        response = self.client.get(url, {
            "pagina": "advanced",
            "pagina_avancada": "central_contratos",
            "dispositivo": "tablet",
        })
        self.assertEqual(response.status_code, 200)
        navigation = response.context["preview"]["advanced_pages"]
        self.assertEqual(len(navigation), 1)
        self.assertTrue(navigation[0]["active"])
        self.assertContains(response, 'data-active="1"')
        self.assertContains(response, "const preserved=['papel','dispositivo','entidade','estado','relatorio']")
        self.assertContains(response, "q.set('pagina_avancada',id)")
        self.assertContains(response, "a.dataset.advancedPageLink=item.dataset.pageId")

    def test_designer_referer_returns_to_same_advanced_page(self):
        self.client.force_login(self.user)
        designer_url = reverse("sistema:page_designer", args=[self.sistema.pk]) + "?pagina=central_contratos"
        preview_url = reverse("sistema:application_preview", args=[self.sistema.pk])
        response = self.client.get(preview_url, HTTP_REFERER=f"http://testserver{designer_url}")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sistema/application_preview_advanced.html")
        self.assertEqual(response.context["preview"]["advanced_page"]["id"], "central_contratos")
        self.assertContains(response, 'data-advanced-page-id="central_contratos"')

    def test_explicit_preview_page_kind_wins_over_designer_referer(self):
        self.client.force_login(self.user)
        designer_url = reverse("sistema:page_designer", args=[self.sistema.pk]) + "?pagina=central_contratos"
        preview_url = reverse("sistema:application_preview", args=[self.sistema.pk])
        response = self.client.get(preview_url, {"pagina": "dashboard"}, HTTP_REFERER=f"http://testserver{designer_url}")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.context["preview"]["page_kind"], "advanced")

    def test_invalid_role_hides_collection_page_fail_closed(self):
        preview = build_preview_shell(self.sistema, selected_role_id="papel-inexistente")
        build_advanced_page_preview(self.sistema, preview, "central_contratos")
        self.assertFalse(preview["advanced_page"]["allowed"])
        self.assertEqual(preview["advanced_pages"], [])
