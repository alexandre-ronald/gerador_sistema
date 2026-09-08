import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Sistema, VersaoGeracao


class WorkspaceDesignerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="workspace-designer", password="x")
        self.sistema = Sistema.objects.create(nome="Workspace Teste", usuario=self.user)
        self.version = VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={
                "dashboard": {"enabled": True, "title": "Painel Executivo", "widgets": []},
                "marcador_existente": {"preservar": True},
            },
        )
        self.client.force_login(self.user)

    def _config(self, destination=None):
        return {
            "version": 1,
            "default_workspace": "gestao",
            "workspaces": [
                {
                    "id": "gestao",
                    "label": "Gestão",
                    "description": "Operação principal",
                    "enabled": True,
                    "order": 0,
                    "home": "painel",
                    "sections": [
                        {
                            "id": "visao_geral",
                            "label": "Visão geral",
                            "enabled": True,
                            "order": 0,
                            "items": [
                                {
                                    "id": "painel",
                                    "label": "Painel Executivo",
                                    "enabled": True,
                                    "order": 0,
                                    "destination": destination or {"kind": "dashboard", "ref": "dashboard"},
                                }
                            ],
                        }
                    ],
                }
            ],
        }

    def test_designer_renders_business_oriented_interface_and_catalog(self):
        response = self.client.get(reverse("sistema:workspace_designer", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "sistema/workspace_designer.html")
        self.assertContains(response, "Espaços de trabalho")
        self.assertContains(response, "Organização do trabalho")
        self.assertContains(response, "Mover workspace para cima")
        self.assertContains(response, "Mover seção para cima")
        self.assertContains(response, "Mover experiência para cima")
        catalog = json.loads(response.context["experience_catalog_json"])
        self.assertIn({"kind": "dashboard", "ref": "dashboard", "label": "Painel Executivo", "group": "Painéis"}, catalog)

    def test_save_persists_normalized_workspace_contract(self):
        response = self.client.post(
            reverse("sistema:salvar_workspace_designer", args=[self.sistema.pk]),
            data=json.dumps({"workspaces": self._config()}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.version.refresh_from_db()
        stored = self.version.estrutura_json["workspaces"]
        self.assertEqual(stored["default_workspace"], "gestao")
        self.assertEqual(stored["workspaces"][0]["home"], "painel")

    def test_save_preserves_explicit_workspace_section_and_item_order(self):
        config = self._config()
        workspace = config["workspaces"][0]
        workspace["order"] = 7
        workspace["sections"][0]["order"] = 5
        workspace["sections"][0]["items"][0]["order"] = 3
        response = self.client.post(
            reverse("sistema:salvar_workspace_designer", args=[self.sistema.pk]),
            data=json.dumps({"workspaces": config}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        stored = response.json()["workspaces"]["workspaces"][0]
        self.assertEqual(stored["order"], 7)
        self.assertEqual(stored["sections"][0]["order"], 5)
        self.assertEqual(stored["sections"][0]["items"][0]["order"], 3)

    def test_save_migrates_placeholder_ids_to_semantic_stable_ids(self):
        config = self._config()
        config["default_workspace"] = "novo_workspace"
        workspace = config["workspaces"][0]
        workspace.update({"id": "novo_workspace", "label": "Gestão de Fornecedores", "home": "novo_item"})
        section = workspace["sections"][0]
        section.update({"id": "nova_secao", "label": "Operação"})
        item = section["items"][0]
        item.update({"id": "novo_item", "label": "Fornecedores"})

        response = self.client.post(
            reverse("sistema:salvar_workspace_designer", args=[self.sistema.pk]),
            data=json.dumps({"workspaces": config}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        stored = response.json()["workspaces"]
        self.assertEqual(stored["default_workspace"], "gestao_de_fornecedores")
        self.assertEqual(stored["workspaces"][0]["id"], "gestao_de_fornecedores")
        self.assertEqual(stored["workspaces"][0]["sections"][0]["id"], "operacao")
        self.assertEqual(stored["workspaces"][0]["sections"][0]["items"][0]["id"], "fornecedores")
        self.assertEqual(stored["workspaces"][0]["home"], "fornecedores")

    def test_save_keeps_existing_semantic_ids_stable_when_labels_change(self):
        config = self._config()
        config["workspaces"][0]["label"] = "Gestão Renomeada"
        config["workspaces"][0]["sections"][0]["label"] = "Outra seção"
        config["workspaces"][0]["sections"][0]["items"][0]["label"] = "Outro painel"
        response = self.client.post(
            reverse("sistema:salvar_workspace_designer", args=[self.sistema.pk]),
            data=json.dumps({"workspaces": config}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        stored = response.json()["workspaces"]
        self.assertEqual(stored["default_workspace"], "gestao")
        self.assertEqual(stored["workspaces"][0]["id"], "gestao")
        self.assertEqual(stored["workspaces"][0]["sections"][0]["id"], "visao_geral")
        self.assertEqual(stored["workspaces"][0]["sections"][0]["items"][0]["id"], "painel")

    def test_save_preserves_other_draft_contracts(self):
        self.client.post(
            reverse("sistema:salvar_workspace_designer", args=[self.sistema.pk]),
            data=json.dumps({"workspaces": self._config()}),
            content_type="application/json",
        )
        self.version.refresh_from_db()
        self.assertEqual(self.version.estrutura_json["marcador_existente"], {"preservar": True})
        self.assertTrue(self.version.estrutura_json["dashboard"]["enabled"])

    def test_save_rejects_destination_that_is_not_available(self):
        response = self.client.post(
            reverse("sistema:salvar_workspace_designer", args=[self.sistema.pk]),
            data=json.dumps({"workspaces": self._config({"kind": "dashboard", "ref": "inexistente"})}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["erro"]["code"], "workspace_destination_not_found")

    def test_designer_is_scoped_to_system_owner(self):
        other = get_user_model().objects.create_user(username="other-workspace-user", password="x")
        self.client.force_login(other)
        response = self.client.get(reverse("sistema:workspace_designer", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 404)
