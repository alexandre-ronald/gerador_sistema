import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase

from sistema.models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from sistema.services import GeradorService


class GeneratedWorkspaceNavigationTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="workspace-generator",
            password="test",
        )
        self.sistema = Sistema.objects.create(
            usuario=user,
            nome="Operação de Contratos",
            caminho_geracao="/tmp/djangoforge-workspace-test",
        )
        modulo = Modulo.objects.create(sistema=self.sistema, nome="contratos")
        self.entidade = Entidade.objects.create(
            modulo=modulo,
            nome="Contrato",
            nome_plural="Contratos",
            gerar_crud_views=True,
        )
        Campo.objects.create(
            entidade=self.entidade,
            nome="numero",
            tipo="CharField",
            max_length=30,
        )
        Campo.objects.create(
            entidade=self.entidade,
            nome="status",
            tipo="CharField",
            max_length=30,
        )
        self.versao = VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={},
        )

    def _generate_context_processor(self, structure):
        self.versao.estrutura_json = structure
        self.versao.save(update_fields=["estrutura_json"])
        with tempfile.TemporaryDirectory() as temp_dir:
            self.sistema.caminho_geracao = temp_dir
            self.sistema.save(update_fields=["caminho_geracao"])
            GeradorService(self.sistema.id).gerar_projeto_completo()
            path = Path(temp_dir) / self.sistema.slug.replace("-", "_") / "context_processors.py"
            self.assertTrue(path.exists())
            return path.read_text(encoding="utf-8")

    def _workspace_structure(self):
        return {
            "workspaces": {
                "version": 1,
                "default_workspace": "gestao_contratos",
                "workspaces": [
                    {
                        "id": "gestao_contratos",
                        "label": "Gestão de Contratos",
                        "enabled": True,
                        "home": "contratos",
                        "sections": [
                            {
                                "id": "operacao",
                                "label": "Operação",
                                "items": [
                                    {
                                        "id": "contratos",
                                        "label": "Contratos ativos",
                                        "destination": {
                                            "kind": "crud",
                                            "ref": "Contrato",
                                            "operation": "list",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        }

    def test_real_generation_materializes_workspace_navigation(self):
        content = self._generate_context_processor(self._workspace_structure())
        self.assertIn("'default_workspace': 'gestao_contratos'", content)
        self.assertIn("'label': 'Gestão de Contratos'", content)
        self.assertIn("'label': 'Operação'", content)
        self.assertIn("_workspace_projection(request)", content)
        self.assertIn("rendered_modules = modules if workspace_modules is None else workspace_modules", content)

    def test_real_generation_materializes_workspace_deep_link_context(self):
        content = self._generate_context_processor(self._workspace_structure())
        compile(content, "context_processors.py", "exec")
        self.assertIn('request.GET.get("workspace")', content)
        self.assertIn('request.GET.get("workspace_item")', content)
        self.assertIn('"workspace_section_label": section.get("label")', content)
        self.assertIn('"navigation_workspace_context": workspace_context', content)
        self.assertIn('if not item.get("is_active"):', content)

    def test_workspace_context_falls_back_to_active_item_in_default_workspace(self):
        content = self._generate_context_processor(self._workspace_structure())
        compile(content, "context_processors.py", "exec")
        self.assertIn("if requested_workspace or requested_item:", content)
        self.assertIn('workspace_projection.get("active_workspace")', content)
        self.assertIn('if item.get("is_active"):', content)
        self.assertIn("return _workspace_context_payload(workspace, section, item)", content)

    def test_workspace_context_drives_generated_runtime_breadcrumb_labels(self):
        content = self._generate_context_processor(self._workspace_structure())
        compile(content, "context_processors.py", "exec")
        self.assertIn("def _workspace_current_navigation(workspace_context, fallback):", content)
        self.assertIn('"module_label": workspace_context.get("workspace_label")', content)
        self.assertIn('f"{section_label} › {item_label}"', content)
        self.assertIn("current_navigation = _workspace_current_navigation(", content)
        self.assertIn('"navigation_current": current_navigation', content)

    def test_workspace_projection_flattens_report_presentation(self):
        content = self._generate_context_processor(self._workspace_structure())
        compile(content, "context_processors.py", "exec")
        self.assertIn('"workspace_destination_kind": destination.get("kind")', content)
        self.assertIn('"is_report": False if destination.get("kind") == "report"', content)
        self.assertIn('"group_label": "" if destination.get("kind") == "report"', content)

    def test_workflow_workspace_destination_reuses_entity_list_navigation(self):
        content = self._generate_context_processor(
            {
                "workflows": {
                    "Contrato": {
                        "enabled": True,
                        "state_field": "status",
                        "initial_state": "rascunho",
                        "states": [
                            {
                                "id": "rascunho",
                                "label": "Rascunho",
                                "final": False,
                                "order": 0,
                            },
                            {
                                "id": "aprovado",
                                "label": "Aprovado",
                                "final": True,
                                "order": 1,
                            },
                        ],
                        "transitions": [
                            {
                                "id": "aprovar",
                                "label": "Aprovar",
                                "from": ["rascunho"],
                                "to": "aprovado",
                                "enabled": True,
                                "confirm": False,
                                "confirm_message": "",
                                "order": 0,
                            }
                        ],
                    }
                },
                "workspaces": {
                    "version": 1,
                    "default_workspace": "fiscalizacao",
                    "workspaces": [
                        {
                            "id": "fiscalizacao",
                            "label": "Fiscalização",
                            "enabled": True,
                            "home": "fluxo_contratos",
                            "sections": [
                                {
                                    "id": "operacao",
                                    "label": "Operação",
                                    "items": [
                                        {
                                            "id": "fluxo_contratos",
                                            "label": "Fluxo de Contratos",
                                            "destination": {
                                                "kind": "workflow",
                                                "ref": "Contrato",
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
            }
        )
        self.assertIn("'kind': 'workflow'", content)
        self.assertIn("'ref': 'Contrato'", content)
        self.assertIn('index[("workflow", item.get("entity_name"))] = item', content)
        self.assertIn('"url_name": "contratos:contrato_list"', content)
        self.assertNotIn("workflow/", content)

    def test_real_generation_without_workspace_preserves_legacy_navigation_fallback(self):
        content = self._generate_context_processor({})
        self.assertIn("'workspaces': []", content)
        self.assertIn('if not workspace_projection.get("configured"):', content)
        self.assertIn("return None", content)
        self.assertIn("rendered_modules = modules if workspace_modules is None else workspace_modules", content)

    def test_runtime_resolves_requested_visible_workspace_before_default(self):
        content = self._generate_context_processor(self._workspace_structure())
        compile(content, "context_processors.py", "exec")
        self.assertIn("def _resolve_active_workspace(workspace_projection, requested_workspace=\"\"):", content)
        self.assertIn("if requested_workspace:", content)
        self.assertIn('item.get("id") == requested_workspace', content)
        self.assertIn('requested_workspace = str(request.GET.get("workspace") or "").strip()', content)
        self.assertIn('"active_workspace": active_workspace', content)
        self.assertIn('workspace_projection.get("active_workspace")', content)
