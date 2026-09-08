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

    def test_real_generation_materializes_workspace_navigation(self):
        content = self._generate_context_processor(
            {
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
        )
        self.assertIn("'default_workspace': 'gestao_contratos'", content)
        self.assertIn("'label': 'Gestão de Contratos'", content)
        self.assertIn("'label': 'Operação'", content)
        self.assertIn("_workspace_projection(request)", content)
        self.assertIn("rendered_modules = modules if workspace_modules is None else workspace_modules", content)

    def test_real_generation_without_workspace_preserves_legacy_navigation_fallback(self):
        content = self._generate_context_processor({})
        self.assertIn("'workspaces': []", content)
        self.assertIn('if not workspace_projection.get("configured"):', content)
        self.assertIn("return None", content)
        self.assertIn("rendered_modules = modules if workspace_modules is None else workspace_modules", content)
