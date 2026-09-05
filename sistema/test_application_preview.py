from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .application_preview import build_preview_shell
from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao


class ApplicationPreviewShellTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="preview", password="test123")
        self.other = get_user_model().objects.create_user(username="other", password="test123")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Gestão de Contratos",
            tipo_menu="lateral",
            interface_modo="escuro",
            interface_densidade="compacta",
            interface_nome="Contratos 360",
            interface_cor_primaria="#2563eb",
            interface_cor_destaque="#7c3aed",
            interface_breadcrumb=True,
            interface_busca=True,
            interface_menu_usuario=True,
        )
        contratos = Modulo.objects.create(sistema=self.sistema, nome="Contratos")
        cadastros = Modulo.objects.create(sistema=self.sistema, nome="Cadastros")
        self.contrato = Entidade.objects.create(
            modulo=contratos,
            nome="Contrato",
            nome_plural="Contratos",
            gerar_crud_views=True,
        )
        self.fornecedor = Entidade.objects.create(
            modulo=cadastros,
            nome="Fornecedor",
            nome_plural="Fornecedores",
            gerar_crud_views=True,
        )
        Entidade.objects.create(
            modulo=cadastros,
            nome="Interno",
            nome_plural="Internos",
            gerar_crud_views=False,
        )
        Campo.objects.create(
            entidade=self.contrato,
            nome="numero",
            tipo="CharField",
            verbose_name="Número",
            help_text="Informe o número oficial do contrato.",
        )
        Campo.objects.create(
            entidade=self.contrato,
            nome="objeto",
            tipo="CharField",
            verbose_name="Objeto",
            blank=True,
        )
        Campo.objects.create(
            entidade=self.contrato,
            nome="valor",
            tipo="DecimalField",
            verbose_name="Valor",
        )
        Campo.objects.create(
            entidade=self.fornecedor,
            nome="nome",
            tipo="CharField",
            verbose_name="Nome",
        )
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "forms": {
                    "Contrato": {
                        "title": "Cadastro de contrato",
                        "sections": [
                            {
                                "id": "dados_principais",
                                "title": "Dados principais",
                                "description": "Identificação do instrumento contratual.",
                                "order": 0,
                            }
                        ],
                        "fields": [
                            {
                                "name": "numero",
                                "order": 0,
                                "section": "dados_principais",
                                "visible": True,
                                "readonly": False,
                                "width": 4,
                                "label": "Número do contrato",
                                "placeholder": "000/2026",
                                "help_text": "Informe o número oficial do contrato.",
                                "widget": "text",
                            },
                            {
                                "name": "objeto",
                                "order": 1,
                                "section": "dados_principais",
                                "visible": True,
                                "readonly": False,
                                "width": 8,
                                "label": "Objeto contratual",
                                "placeholder": "Descreva o objeto",
                                "help_text": "",
                                "widget": "textarea",
                            },
                            {
                                "name": "valor",
                                "order": 2,
                                "section": "",
                                "visible": False,
                                "readonly": False,
                                "width": 4,
                                "label": "Valor",
                                "placeholder": "",
                                "help_text": "",
                                "widget": "number",
                            },
                        ],
                    }
                },
                "cruds": {
                    "Contrato": {
                        "title": "Gestão de contratos",
                        "page_size": 50,
                        "default_order": "numero",
                        "columns": [
                            {"field": "numero", "label": "Contrato", "order": 0, "visible": True, "sortable": True},
                            {"field": "objeto", "label": "Objeto", "order": 1, "visible": True, "sortable": True},
                            {"field": "valor", "label": "Valor", "order": 2, "visible": False, "sortable": True},
                        ],
                        "search": {
                            "enabled": True,
                            "fields": ["numero", "objeto"],
                            "placeholder": "Pesquisar contratos",
                        },
                        "filters": [
                            {"field": "numero", "label": "Número", "type": "text", "order": 0},
                        ],
                        "actions": {"create": True, "view": True, "edit": True, "delete": False},
                    }
                },
            },
        )

    def test_projects_interface_designer_into_preview_shell(self):
        preview = build_preview_shell(self.sistema)
        self.assertEqual(preview["application"]["name"], "Contratos 360")
        self.assertEqual(preview["interface"]["menu"], "lateral")
        self.assertEqual(preview["interface"]["mode"], "escuro")
        self.assertEqual(preview["interface"]["density"], "compacta")
        self.assertEqual(preview["interface"]["primary"], "#2563eb")
        self.assertEqual(preview["interface"]["accent"], "#7c3aed")
        self.assertTrue(preview["interface"]["breadcrumb"])
        self.assertTrue(preview["interface"]["search"])
        self.assertTrue(preview["interface"]["user_menu"])

    def test_navigation_is_deterministic_and_matches_generated_crud_scope(self):
        first = build_preview_shell(self.sistema)
        second = build_preview_shell(self.sistema)
        self.assertEqual(first, second)
        modules = first["navigation"]["modules"]
        self.assertEqual([item["label"] for item in modules], ["Cadastros", "Contratos"])
        self.assertEqual([item["label"] for item in modules[0]["items"]], ["Fornecedores"])
        self.assertEqual([item["label"] for item in modules[1]["items"]], ["Contratos"])
        self.assertNotIn("Internos", str(modules))

    def test_projects_crud_designer_into_list_preview(self):
        preview = build_preview_shell(self.sistema, selected_entity_id=self.contrato.pk)
        page = preview["list_page"]
        self.assertEqual(page["entity"], "Contrato")
        self.assertEqual(page["area"], "Contratos")
        self.assertEqual(page["title"], "Gestão de contratos")
        self.assertEqual(page["page_size"], 50)
        self.assertEqual(page["default_order"], "numero")
        self.assertEqual([item["label"] for item in page["columns"]], ["Contrato", "Objeto"])
        self.assertNotIn("Valor", [item["label"] for item in page["columns"]])
        self.assertEqual(page["search"]["placeholder"], "Pesquisar contratos")
        self.assertEqual(page["filters"][0]["label"], "Número")
        self.assertEqual(page["filters"][0]["kind_label"], "Texto")
        self.assertTrue(page["actions"]["create"])
        self.assertTrue(page["actions"]["view"])
        self.assertTrue(page["actions"]["edit"])
        self.assertFalse(page["actions"]["delete"])
        self.assertEqual(page["demo_count"], 4)
        self.assertEqual(page["rows"][0]["values"][0]["value"], "Número 01")

    def test_projects_form_designer_into_form_preview(self):
        preview = build_preview_shell(
            self.sistema,
            selected_entity_id=self.contrato.pk,
            page_kind="form",
        )
        page = preview["form_page"]
        self.assertEqual(preview["page_kind"], "form")
        self.assertEqual(page["entity"], "Contrato")
        self.assertEqual(page["area"], "Contratos")
        self.assertEqual(page["title"], "Cadastro de contrato")
        self.assertEqual(page["visible_count"], 2)
        self.assertEqual([section["title"] for section in page["sections"]], ["Dados principais"])
        fields = page["sections"][0]["fields"]
        self.assertEqual([field["label"] for field in fields], ["Número do contrato", "Objeto contratual"])
        self.assertEqual(fields[0]["width"], 4)
        self.assertEqual(fields[1]["width"], 8)
        self.assertEqual(fields[0]["widget"], "text")
        self.assertEqual(fields[1]["widget"], "textarea")
        self.assertTrue(fields[0]["required"])
        self.assertFalse(fields[1]["required"])
        self.assertNotIn("Valor", [field["label"] for field in page["visible_fields"]])

    def test_list_and_form_previews_are_deterministic_for_same_contract(self):
        first = build_preview_shell(self.sistema, selected_entity_id=self.contrato.pk, page_kind="form")
        second = build_preview_shell(self.sistema, selected_entity_id=self.contrato.pk, page_kind="form")
        self.assertEqual(first["list_page"], second["list_page"])
        self.assertEqual(first["form_page"], second["form_page"])

    def test_unknown_selected_entity_falls_back_to_available_crud(self):
        preview = build_preview_shell(self.sistema, selected_entity_id=999999)
        self.assertEqual(preview["list_page"]["entity"], "Fornecedor")

    def test_unknown_page_kind_falls_back_to_list(self):
        preview = build_preview_shell(
            self.sistema,
            selected_entity_id=self.contrato.pk,
            page_kind="anything",
        )
        self.assertEqual(preview["page_kind"], "list")
        self.assertIsNone(preview["form_page"])

    def test_preview_does_not_persist_parallel_contract(self):
        build_preview_shell(self.sistema, selected_entity_id=self.contrato.pk, page_kind="form")
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        self.assertNotIn("preview", draft.estrutura_json)
        self.assertNotIn("preview_studio", draft.estrutura_json)

    def test_preview_view_renders_shell_for_owner(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sistema:application_preview", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Preview Studio")
        self.assertContains(response, "Contratos 360")
        self.assertContains(response, "application-preview-shell")
        self.assertContains(response, "Fornecedores")
        self.assertContains(response, "Contratos")
        self.assertNotContains(response, ">Internos<")

    def test_preview_view_selects_and_renders_crud_list(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk]),
            {"entidade": self.contrato.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestão de contratos")
        self.assertContains(response, "Pesquisar contratos")
        self.assertContains(response, "registros demonstrativos")
        self.assertContains(response, "Número 01")
        self.assertContains(response, "Objeto 01")
        self.assertContains(response, f"?entidade={self.contrato.pk}&pagina=form")
        self.assertNotContains(response, "<th>Valor")
        self.assertNotContains(response, 'title="Excluir"')

    def test_preview_view_selects_and_renders_form(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("sistema:application_preview", args=[self.sistema.pk]),
            {"entidade": self.contrato.pk, "pagina": "form"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-preview-page="form"')
        self.assertContains(response, "Cadastro de contrato")
        self.assertContains(response, "Dados principais")
        self.assertContains(response, "Identificação do instrumento contratual.")
        self.assertContains(response, "Número do contrato")
        self.assertContains(response, "000/2026")
        self.assertContains(response, "Informe o número oficial do contrato.")
        self.assertContains(response, "Objeto contratual")
        self.assertContains(response, "Descreva o objeto")
        self.assertContains(response, "col-md-4 preview-form-field")
        self.assertContains(response, "col-md-8 preview-form-field")
        self.assertNotContains(response, 'data-field="valor"')

    def test_preview_view_is_scoped_to_owner(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("sistema:application_preview", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 404)
