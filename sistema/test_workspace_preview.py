from types import SimpleNamespace
from django.test import SimpleTestCase
from .workspace_preview import project_workspace_preview

class WorkspacePreviewTests(SimpleTestCase):
    def setUp(self):
        self.entities=[SimpleNamespace(nome="Fornecedor",pk=10),SimpleNamespace(nome="Contrato",pk=20)]
        self.structure={"workspaces":{"version":1,"default_workspace":"gestao","workspaces":[{"id":"gestao","label":"Gestão","home":"fornecedores","sections":[{"id":"operacao","label":"Operação","items":[{"id":"fornecedores","label":"Fornecedores","destination":{"kind":"crud","ref":"Fornecedor","operation":"list"}},{"id":"contratos","label":"Contratos","destination":{"kind":"crud","ref":"Contrato","operation":"list"}},{"id":"relatorio","label":"Relatório","destination":{"kind":"report","ref":"Contrato:ativos"}}]}]}]},"rbac":{"enabled":True,"entities":{"Fornecedor":{"roles":{"gestor":["list"],"fiscal":[]}},"Contrato":{"roles":{"gestor":["list"],"fiscal":["list"]}}},"reports":{"Contrato":{"ativos":["gestor"]}}}}
    def role(self,role_id):return {"active":True,"invalid_role":False,"selected_role_id":role_id}
    def test_gestor_sees_authorized_workspace_items(self):
        preview=project_workspace_preview(self.structure,role_simulation=self.role("gestor"),entities=self.entities); items=preview["selected"]["sections"][0]["items"]; self.assertEqual([item["id"] for item in items],["fornecedores","contratos","relatorio"])
    def test_fiscal_sees_only_contracts(self):
        preview=project_workspace_preview(self.structure,role_simulation=self.role("fiscal"),entities=self.entities); items=preview["selected"]["sections"][0]["items"]; self.assertEqual([item["id"] for item in items],["contratos"]); self.assertEqual(preview["selected"]["home"],"contratos")
    def test_invalid_role_fails_closed(self):
        preview=project_workspace_preview(self.structure,role_simulation={"active":False,"invalid_role":True,"selected_role_id":""},entities=self.entities); self.assertEqual(preview["workspaces"],[]); self.assertIsNone(preview["selected"])
    def test_design_view_does_not_apply_role_filter(self):
        preview=project_workspace_preview(self.structure,role_simulation={"active":False,"invalid_role":False,"selected_role_id":""},entities=self.entities); self.assertEqual(len(preview["selected"]["sections"][0]["items"]),3)
    def test_destination_urls_are_projected_from_stable_refs(self):
        preview=project_workspace_preview(self.structure,role_simulation=self.role("gestor"),entities=self.entities); items={item["id"]:item for item in preview["selected"]["sections"][0]["items"]}; self.assertEqual(items["fornecedores"]["url"],"?entidade=10&pagina=list"); self.assertEqual(items["relatorio"]["url"],"?entidade=20&pagina=report&relatorio=ativos")
