from types import SimpleNamespace

from django.test import SimpleTestCase

from sistema.workspace_preview import project_workspace_preview
from sistema.workspace_visibility import visible_workspace_config


class WorkspaceEndToEndEquivalenceTests(SimpleTestCase):
    """GEN-072.9 — Preview e runtime partem da mesma projeção RBAC de Workspace."""

    def setUp(self):
        self.structure = {
            "rbac": {
                "enabled": True,
                "roles": [
                    {"id": "gestor", "label": "Gestor", "group": "Gestor", "order": 0},
                    {"id": "fiscal", "label": "Fiscal", "group": "Fiscal", "order": 1},
                ],
                "entities": {
                    "Fornecedor": {"roles": {"gestor": ["list", "view"]}, "transitions": {}},
                    "Contrato": {
                        "roles": {"gestor": ["list", "view"], "fiscal": ["list", "view"]},
                        "transitions": {},
                    },
                },
                "reports": {"Contrato": {"contratos_ativos": ["gestor"]}},
            },
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
                                    },
                                    {
                                        "id": "contratos",
                                        "label": "Contratos",
                                        "enabled": True,
                                        "destination": {"kind": "crud", "ref": "Contrato", "operation": "list"},
                                    },
                                    {
                                        "id": "relatorio_contratos",
                                        "label": "Relatório de Contratos",
                                        "enabled": True,
                                        "destination": {"kind": "report", "ref": "Contrato:contratos_ativos"},
                                    },
                                ],
                            }
                        ],
                    },
                    {
                        "id": "fiscalizacao",
                        "label": "Fiscalização",
                        "enabled": True,
                        "home": "contratos_fiscais",
                        "sections": [
                            {
                                "id": "rotina",
                                "label": "Rotina",
                                "enabled": True,
                                "items": [
                                    {
                                        "id": "contratos_fiscais",
                                        "label": "Contratos para fiscalizar",
                                        "enabled": True,
                                        "destination": {"kind": "crud", "ref": "Contrato", "operation": "list"},
                                    }
                                ],
                            }
                        ],
                    },
                ],
            },
        }
        self.entities = [
            SimpleNamespace(nome="Fornecedor", pk=10),
            SimpleNamespace(nome="Contrato", pk=20),
        ]

    def _preview_for(self, role_id):
        return project_workspace_preview(
            self.structure,
            role_simulation={"active": True, "selected_role_id": role_id},
            entities=self.entities,
        )

    def _runtime_projection_for(self, role_id):
        return visible_workspace_config(
            self.structure["workspaces"],
            structure=self.structure,
            rbac=self.structure["rbac"],
            role_ids=[role_id],
        )

    @staticmethod
    def _shape(workspaces):
        return [
            (
                workspace["id"],
                [
                    (
                        section["id"],
                        [item["id"] for item in section.get("items") or []],
                    )
                    for section in workspace.get("sections") or []
                ],
            )
            for workspace in workspaces
        ]

    def test_gestor_preview_matches_runtime_visibility_projection(self):
        preview = self._preview_for("gestor")
        runtime = self._runtime_projection_for("gestor")

        self.assertEqual(
            self._shape(preview["workspaces"]),
            self._shape(runtime["workspaces"]),
        )
        self.assertEqual(
            [workspace["id"] for workspace in preview["workspaces"]],
            ["gestao", "fiscalizacao"],
        )
        self.assertEqual(
            [item["id"] for item in preview["workspaces"][0]["sections"][0]["items"]],
            ["fornecedores", "contratos", "relatorio_contratos"],
        )

    def test_fiscal_preview_matches_runtime_visibility_projection(self):
        preview = self._preview_for("fiscal")
        runtime = self._runtime_projection_for("fiscal")

        self.assertEqual(
            self._shape(preview["workspaces"]),
            self._shape(runtime["workspaces"]),
        )
        self.assertEqual(
            [workspace["id"] for workspace in preview["workspaces"]],
            ["gestao", "fiscalizacao"],
        )
        self.assertEqual(
            [item["id"] for item in preview["workspaces"][0]["sections"][0]["items"]],
            ["contratos"],
        )
        self.assertEqual(preview["workspaces"][0]["home"], "contratos")

    def test_contextual_urls_keep_workspace_origin_for_same_destination(self):
        preview = self._preview_for("fiscal")
        gestao_item = preview["workspaces"][0]["sections"][0]["items"][0]
        fiscalizacao_item = preview["workspaces"][1]["sections"][0]["items"][0]

        self.assertIn("workspace=gestao", gestao_item["url"])
        self.assertIn("workspace_item=contratos", gestao_item["url"])
        self.assertIn("workspace=fiscalizacao", fiscalizacao_item["url"])
        self.assertIn("workspace_item=contratos_fiscais", fiscalizacao_item["url"])
