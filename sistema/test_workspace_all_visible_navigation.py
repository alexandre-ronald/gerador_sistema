from types import SimpleNamespace

from django.test import SimpleTestCase

from sistema.workspace_preview import project_workspace_preview


class WorkspaceAllVisibleNavigationTests(SimpleTestCase):
    def test_preview_projects_all_visible_workspaces_as_navigation_groups(self):
        structure = {
            "workspaces": {
                "version": 1,
                "default_workspace": "gestao",
                "workspaces": [
                    {
                        "id": "gestao",
                        "label": "Gestão de Fornecedores",
                        "enabled": True,
                        "home": "fornecedores",
                        "sections": [
                            {
                                "id": "operacao",
                                "label": "Operação",
                                "enabled": True,
                                "items": [
                                    {
                                        "id": "fornecedores",
                                        "label": "Fornecedores",
                                        "enabled": True,
                                        "destination": {"kind": "crud", "ref": "Fornecedor", "operation": "list"},
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "id": "fiscalizacao",
                        "label": "Fiscalização",
                        "enabled": True,
                        "home": "contratos",
                        "sections": [
                            {
                                "id": "rotina",
                                "label": "Rotina",
                                "enabled": True,
                                "items": [
                                    {
                                        "id": "contratos",
                                        "label": "Contratos",
                                        "enabled": True,
                                        "destination": {"kind": "crud", "ref": "Contrato", "operation": "list"},
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        }
        entities = [SimpleNamespace(nome="Fornecedor", pk=10), SimpleNamespace(nome="Contrato", pk=20)]

        projection = project_workspace_preview(
            structure,
            role_simulation={},
            entities=entities,
        )

        self.assertEqual(
            [group["label"] for group in projection["navigation_groups"]],
            ["Gestão de Fornecedores", "Fiscalização"],
        )
        self.assertEqual(projection["navigation_groups"][0]["sections"][0]["label"], "Operação")
        self.assertEqual(projection["navigation_groups"][1]["sections"][0]["label"], "Rotina")
        self.assertIn("workspace=gestao", projection["navigation_groups"][0]["sections"][0]["items"][0]["url"])
        self.assertIn("workspace=fiscalizacao", projection["navigation_groups"][1]["sections"][0]["items"][0]["url"])
