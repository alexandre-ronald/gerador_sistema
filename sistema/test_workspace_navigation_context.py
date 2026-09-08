from django.test import SimpleTestCase

from .workspace_navigation_context import (
    resolve_active_workspace,
    resolve_workspace_navigation_context,
)


class WorkspaceNavigationContextTests(SimpleTestCase):
    def setUp(self):
        self.projection = {
            "configured": True,
            "default_workspace": "gestao",
            "workspaces": [
                {
                    "id": "gestao",
                    "label": "Gestão de Contratos",
                    "home": "contratos",
                    "sections": [
                        {
                            "id": "operacao",
                            "label": "Operação",
                            "items": [
                                {
                                    "workspace_item_id": "contratos",
                                    "label": "Contratos ativos",
                                    "url_name": "contratos:contrato_list",
                                },
                                {
                                    "workspace_item_id": "relatorio",
                                    "label": "Relatório de Contratos",
                                    "url_name": "contratos:contrato_relatorio",
                                },
                            ],
                        }
                    ],
                },
                {
                    "id": "fiscalizacao",
                    "label": "Fiscalização",
                    "home": "acompanhar",
                    "sections": [
                        {
                            "id": "rotina",
                            "label": "Rotina",
                            "items": [
                                {
                                    "workspace_item_id": "acompanhar",
                                    "label": "Acompanhar contratos",
                                    "url_name": "contratos:contrato_list",
                                }
                            ],
                        }
                    ],
                },
            ],
        }

    def test_requested_visible_workspace_becomes_active(self):
        workspace = resolve_active_workspace(
            self.projection,
            workspace_id="fiscalizacao",
        )
        self.assertEqual(workspace["id"], "fiscalizacao")

    def test_missing_or_invisible_workspace_falls_back_to_visible_default(self):
        workspace = resolve_active_workspace(
            self.projection,
            workspace_id="administracao",
        )
        self.assertEqual(workspace["id"], "gestao")

    def test_missing_visible_default_falls_back_to_first_visible_workspace(self):
        projection = {**self.projection, "default_workspace": "administracao"}
        workspace = resolve_active_workspace(projection)
        self.assertEqual(workspace["id"], "gestao")

    def test_empty_visible_projection_has_no_active_workspace(self):
        workspace = resolve_active_workspace(
            {"configured": True, "default_workspace": "gestao", "workspaces": []},
            workspace_id="gestao",
        )
        self.assertIsNone(workspace)

    def test_deep_link_resolves_stable_workspace_and_item_ids(self):
        context = resolve_workspace_navigation_context(
            self.projection,
            workspace_id="gestao",
            item_id="relatorio",
        )
        self.assertEqual(context["workspace_id"], "gestao")
        self.assertEqual(context["section_id"], "operacao")
        self.assertEqual(context["item_id"], "relatorio")
        self.assertEqual(context["url_name"], "contratos:contrato_relatorio")
        self.assertFalse(context["is_home"])
        self.assertEqual(
            [crumb["label"] for crumb in context["breadcrumbs"]],
            ["Gestão de Contratos", "Operação", "Relatório de Contratos"],
        )

    def test_missing_item_falls_back_to_visible_workspace_home(self):
        context = resolve_workspace_navigation_context(
            self.projection,
            workspace_id="gestao",
            item_id="inexistente",
        )
        self.assertEqual(context["item_id"], "contratos")
        self.assertTrue(context["is_home"])

    def test_requested_second_workspace_resolves_its_own_home(self):
        context = resolve_workspace_navigation_context(
            self.projection,
            workspace_id="fiscalizacao",
            item_id="",
        )
        self.assertEqual(context["workspace_id"], "fiscalizacao")
        self.assertEqual(context["section_id"], "rotina")
        self.assertEqual(context["item_id"], "acompanhar")
        self.assertTrue(context["is_home"])

    def test_missing_workspace_falls_back_to_visible_default_workspace(self):
        context = resolve_workspace_navigation_context(
            self.projection,
            workspace_id="inexistente",
            item_id="relatorio",
        )
        self.assertEqual(context["workspace_id"], "gestao")
        self.assertEqual(context["item_id"], "relatorio")

    def test_empty_visible_projection_fails_closed(self):
        context = resolve_workspace_navigation_context(
            {"configured": True, "default_workspace": "gestao", "workspaces": []},
            workspace_id="gestao",
            item_id="contratos",
        )
        self.assertIsNone(context)
