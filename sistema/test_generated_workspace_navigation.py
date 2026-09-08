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

    def _generate_file(self, structure, relative_path):
        self.versao.estrutura_json = structure
        self.versao.save(update_fields=["estrutura_json"])
        with tempfile.TemporaryDirectory() as temp_dir:
            self.sistema.caminho_geracao = temp_dir
            self.sistema.save(update_fields=["caminho_geracao"])
            GeradorService(self.sistema.id).gerar_projeto_completo()
            project_root = Path(temp_dir) / self.sistema.slug.replace("-", "_")
            path = project_root / relative_path
            self.assertTrue(path.exists())
            return path.read_text(encoding="utf-8")

    def _generate_context_processor(self, structure):
        return self._generate_file(structure, "context_processors.py")

    def _generate_base_template(self, structure):
        # Templates globais são materializados na raiz da geração, enquanto
        # context_processors.py pertence ao pacote Python do projeto.
        return self._generate_file(structure, "../templates/base.html")

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

    def test_workspace_context_falls_back_to_active_item_across_visible_workspaces(self):
        content = self._generate_context_processor(self._workspace_structure())
        compile(content, "context_processors.py", "exec")
        self.assertIn("if requested_workspace or requested_item:", content)
        self.assertIn("for workspace in workspaces:", content)
        self.assertIn('if item.get("is_active"):', content)
        self.assertIn("return _workspace_context_payload(workspace, section, item)", content)
        self.assertNotIn('workspace_projection.get("active_workspace")', content)

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

    def test_runtime_projects_all_visible_workspaces_without_active_workspace_state(self):
        structure = self._workspace_structure()
        structure["workspaces"]["workspaces"].append(
            {
                "id": "fiscalizacao",
                "label": "Fiscalização",
                "enabled": True,
                "home": "contratos_fiscais",
                "sections": [
                    {
                        "id": "rotina",
                        "label": "Rotina",
                        "items": [
                            {
                                "id": "contratos_fiscais",
                                "label": "Contratos para fiscalizar",
                                "destination": {"kind": "crud", "ref": "Contrato", "operation": "list"},
                            }
                        ],
                    }
                ],
            }
        )
        content = self._generate_context_processor(structure)
        compile(content, "context_processors.py", "exec")
        self.assertIn("def _workspace_navigation_modules(workspace_projection):", content)
        self.assertIn("for workspace in workspace_projection.get(\"workspaces\") or []:", content)
        self.assertIn('"workspace_label": workspace.get("label")', content)
        self.assertIn('"workspace_section_label": section.get("label")', content)
        self.assertNotIn("def _resolve_active_workspace", content)
        self.assertNotIn('"active_workspace": active_workspace', content)

    def test_generated_base_preserves_workspace_context_in_navigation_links(self):
        content = self._generate_base_template(self._workspace_structure())
        self.assertIn("?workspace={{ modulo.workspace_id|urlencode }}&workspace_item={{ item.workspace_item_id|urlencode }}", content)

    def test_workflow_workspace_destination_reuses_entity_list_navigation(self):
        content = self._generate_context_processor(
            {
                "workflows": {
                    "Contrato": {
                        "enabled": True,
                        "state_field": "status",
                        "initial_state": "rascunho",
                        "states": [
                            {"id": "rascunho", "label": "Rascunho", "final": False, "order": 0},
                            {"id": "aprovado", "label": "Aprovado", "final": True, "order": 1},
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
                    "default_workspace": "operacao",
                    "workspaces": [
                        {
                            "id": "operacao",
                            "label": "Operação",
                            "enabled": True,
                            "home": "fluxo_contrato",
                            "sections": [
                                {
                                    "id": "fluxos",
                                    "label": "Fluxos",
                                    "items": [
                                        {
                                            "id": "fluxo_contrato",
                                            "label": "Fluxo de Contratos",
                                            "destination": {"kind": "workflow", "ref": "Contrato"},
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
            }
        )
        compile(content, "context_processors.py", "exec")
        self.assertIn('index[("workflow", item.get("entity_name"))] = item', content)
        self.assertIn('"workspace_destination_kind": destination.get("kind")', content)

    def test_generation_without_workspace_preserves_legacy_navigation(self):
        content = self._generate_context_processor({})
        compile(content, "context_processors.py", "exec")
        self.assertIn('return {"configured": False, "workspaces": [], "default_workspace": ""}', content)
        self.assertIn("rendered_modules = modules if workspace_modules is None else workspace_modules", content)
