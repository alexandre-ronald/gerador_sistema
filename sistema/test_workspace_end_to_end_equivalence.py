import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sistema.models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from sistema.services import GeradorService
from sistema.workspace_preview import project_workspace_preview
from sistema.workspace_visibility import visible_workspace_config


class WorkspaceEndToEndEquivalenceTests(TestCase):
    """GEN-072.9 — contrato persistido, Preview e runtime compartilham a mesma projeção RBAC."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="workspace-e2e", password="x")
        self.sistema = Sistema.objects.create(nome="Workspace E2E", usuario=self.user)
        self.version = VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            descricao="Rascunho",
            estrutura_json={},
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="operacao")
        self.fornecedor = Entidade.objects.create(
            modulo=modulo,
            nome="Fornecedor",
            nome_plural="Fornecedores",
            gerar_crud_views=True,
        )
        self.contrato = Entidade.objects.create(
            modulo=modulo,
            nome="Contrato",
            nome_plural="Contratos",
            gerar_crud_views=True,
        )
        Campo.objects.create(entidade=self.fornecedor, nome="nome", tipo="CharField", max_length=120)
        Campo.objects.create(entidade=self.contrato, nome="numero", tipo="CharField", max_length=30)
        self.client.force_login(self.user)
        self.structure = {
            "cruds": {"Fornecedor": {}, "Contrato": {}},
            "reports": {
                "Contrato": [
                    {
                        "id": "contratos_ativos",
                        "title": "Relatório de Contratos",
                        "enabled": True,
                    }
                ]
            },
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
            SimpleNamespace(nome="Fornecedor", pk=self.fornecedor.pk),
            SimpleNamespace(nome="Contrato", pk=self.contrato.pk),
        ]

    def _preview_for(self, structure, role_id):
        return project_workspace_preview(
            structure,
            role_simulation={"active": True, "selected_role_id": role_id},
            entities=self.entities,
        )

    @staticmethod
    def _runtime_projection_for(structure, role_id):
        return visible_workspace_config(
            structure["workspaces"],
            structure=structure,
            rbac=structure["rbac"],
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

    def _persist_workspace_through_designer(self):
        self.version.estrutura_json = {
            "cruds": self.structure["cruds"],
            "reports": self.structure["reports"],
            "rbac": self.structure["rbac"],
            "marcador": {"preservar": True},
        }
        self.version.save(update_fields=["estrutura_json"])
        response = self.client.post(
            reverse("sistema:salvar_workspace_designer", args=[self.sistema.pk]),
            data=json.dumps({"workspaces": self.structure["workspaces"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.version.refresh_from_db()
        return response, self.version.estrutura_json

    def test_gestor_preview_matches_runtime_visibility_projection(self):
        preview = self._preview_for(self.structure, "gestor")
        runtime = self._runtime_projection_for(self.structure, "gestor")
        self.assertEqual(self._shape(preview["workspaces"]), self._shape(runtime["workspaces"]))
        self.assertEqual([workspace["id"] for workspace in preview["workspaces"]], ["gestao", "fiscalizacao"])
        self.assertEqual(
            [item["id"] for item in preview["workspaces"][0]["sections"][0]["items"]],
            ["fornecedores", "contratos", "relatorio_contratos"],
        )

    def test_fiscal_preview_matches_runtime_visibility_projection(self):
        preview = self._preview_for(self.structure, "fiscal")
        runtime = self._runtime_projection_for(self.structure, "fiscal")
        self.assertEqual(self._shape(preview["workspaces"]), self._shape(runtime["workspaces"]))
        self.assertEqual([workspace["id"] for workspace in preview["workspaces"]], ["gestao", "fiscalizacao"])
        self.assertEqual(
            [item["id"] for item in preview["workspaces"][0]["sections"][0]["items"]],
            ["contratos"],
        )
        self.assertEqual(preview["workspaces"][0]["home"], "contratos")

    def test_contextual_urls_keep_workspace_origin_for_same_destination(self):
        preview = self._preview_for(self.structure, "fiscal")
        gestao_item = preview["workspaces"][0]["sections"][0]["items"][0]
        fiscalizacao_item = preview["workspaces"][1]["sections"][0]["items"][0]
        self.assertIn("workspace=gestao", gestao_item["url"])
        self.assertIn("workspace_item=contratos", gestao_item["url"])
        self.assertIn("workspace=fiscalizacao", fiscalizacao_item["url"])
        self.assertIn("workspace_item=contratos_fiscais", fiscalizacao_item["url"])

    def test_designer_persistence_is_the_source_for_role_projections(self):
        response, persisted = self._persist_workspace_through_designer()
        self.assertEqual(persisted["marcador"], {"preservar": True})
        self.assertEqual(persisted["workspaces"], response.json()["workspaces"])
        for role_id in ("gestor", "fiscal"):
            preview = self._preview_for(persisted, role_id)
            runtime = self._runtime_projection_for(persisted, role_id)
            self.assertEqual(self._shape(preview["workspaces"]), self._shape(runtime["workspaces"]))

    def test_persisted_workspace_contract_reaches_real_generated_runtime_artifacts(self):
        _, persisted = self._persist_workspace_through_designer()
        with tempfile.TemporaryDirectory() as temp_dir:
            self.sistema.caminho_geracao = temp_dir
            self.sistema.save(update_fields=["caminho_geracao"])
            GeradorService(self.sistema.pk).gerar_projeto_completo()

            root = Path(temp_dir)
            project_name = self.sistema.slug.replace("-", "_")
            context_candidates = [root / "context_processors.py", root / project_name / "context_processors.py"]
            base_candidates = [root / "templates" / "base.html", root / project_name / "templates" / "base.html"]
            context_path = next((path for path in context_candidates if path.exists()), None)
            base_path = next((path for path in base_candidates if path.exists()), None)

            self.assertIsNotNone(context_path)
            self.assertIsNotNone(base_path)
            context = context_path.read_text(encoding="utf-8")
            base = base_path.read_text(encoding="utf-8")
            compile(context, "context_processors.py", "exec")

            self.assertIn(repr(persisted["workspaces"]), context)
            self.assertIn("Gestão de Fornecedores", context)
            self.assertIn("Fiscalização", context)
            self.assertIn("for workspace in workspace_projection.get(\"workspaces\") or []:", context)
            self.assertNotIn("def _resolve_active_workspace", context)
            self.assertNotIn("Trocar Workspace", base)
            self.assertNotIn("navigation_workspaces.active_workspace", base)
            self.assertIn("?workspace={{ modulo.workspace_id|urlencode }}&workspace_item={{ item.workspace_item_id|urlencode }}", base)
