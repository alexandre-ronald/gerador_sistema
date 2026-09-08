from copy import deepcopy
from django.test import SimpleTestCase
from .workspace_visibility import visible_workspace_config,workspace_destination_visible

class WorkspaceVisibilityTests(SimpleTestCase):
    def setUp(self):
        self.rbac={"enabled":True,"roles":[{"id":"gestor","label":"Gestor","description":"","group":"Gestor","order":0},{"id":"fiscal","label":"Fiscal","description":"","group":"Fiscal","order":1}],"entities":{"Fornecedor":{"roles":{"gestor":["list","view"]},"transitions":{}},"Contrato":{"roles":{"gestor":["list","view"],"fiscal":["list","view"]},"transitions":{}}},"reports":{"Contrato":{"contratos_ativos":["gestor"]}}}
        self.structure={"workflows":{"Contrato":{"enabled":True}},"advanced_pages":{"version":1,"pages":[{"id":"central_fornecedor","name":"Central","slug":"central","enabled":True,"context":{"kind":"record","entity":"Fornecedor"},"navigation":{"visible":False,"label":"","icon":"","group":"","order":0},"components":[],"actions":[]}]}}
        self.config={"version":1,"default_workspace":"gestao","workspaces":[{"id":"gestao","label":"Gestão","home":"fornecedores","sections":[{"id":"operacao","label":"Operação","items":[{"id":"fornecedores","label":"Fornecedores","destination":{"kind":"crud","ref":"Fornecedor","operation":"list"}},{"id":"contratos","label":"Contratos","destination":{"kind":"crud","ref":"Contrato","operation":"list"}},{"id":"relatorio","label":"Relatório","destination":{"kind":"report","ref":"Contrato:contratos_ativos"}}]}]}]}
    def test_rbac_disabled_does_not_filter_navigation(self): self.assertTrue(workspace_destination_visible({"kind":"crud","ref":"Fornecedor","operation":"list"},structure=self.structure,rbac={"enabled":False},role_ids=[]))
    def test_crud_visibility_is_derived_from_existing_entity_policy(self):
        destination={"kind":"crud","ref":"Fornecedor","operation":"list"}; self.assertTrue(workspace_destination_visible(destination,structure=self.structure,rbac=self.rbac,role_ids=["gestor"])); self.assertFalse(workspace_destination_visible(destination,structure=self.structure,rbac=self.rbac,role_ids=["fiscal"]))
    def test_report_visibility_uses_existing_report_policy(self):
        destination={"kind":"report","ref":"Contrato:contratos_ativos"}; self.assertTrue(workspace_destination_visible(destination,structure=self.structure,rbac=self.rbac,role_ids=["gestor"])); self.assertFalse(workspace_destination_visible(destination,structure=self.structure,rbac=self.rbac,role_ids=["fiscal"]))
    def test_advanced_record_page_derives_view_permission_from_context_entity(self):
        destination={"kind":"advanced_page","ref":"central_fornecedor"}; self.assertTrue(workspace_destination_visible(destination,structure=self.structure,rbac=self.rbac,role_ids=["gestor"])); self.assertFalse(workspace_destination_visible(destination,structure=self.structure,rbac=self.rbac,role_ids=["fiscal"]))
    def test_workflow_visibility_requires_enabled_workflow_and_entity_list_access(self):
        destination={"kind":"workflow","ref":"Contrato"}; self.assertTrue(workspace_destination_visible(destination,structure=self.structure,rbac=self.rbac,role_ids=["gestor"])); self.assertTrue(workspace_destination_visible(destination,structure=self.structure,rbac=self.rbac,role_ids=["fiscal"])); structure={**self.structure,"workflows":{"Contrato":{"enabled":False}}}; self.assertFalse(workspace_destination_visible(destination,structure=structure,rbac=self.rbac,role_ids=["fiscal"]))
    def test_projection_removes_unauthorized_items_fail_closed(self):
        projected=visible_workspace_config(self.config,structure=self.structure,rbac=self.rbac,role_ids=["fiscal"]); self.assertEqual([item["id"] for item in projected["workspaces"][0]["sections"][0]["items"]],["contratos"])
    def test_disabled_workspace_is_removed(self):
        config=deepcopy(self.config); config["workspaces"][0]["enabled"]=False
        projected=visible_workspace_config(config,structure=self.structure,rbac=self.rbac,role_ids=["gestor"]); self.assertEqual(projected["workspaces"],[]); self.assertEqual(projected["default_workspace"],"")
    def test_disabled_section_is_removed_with_its_items(self):
        config=deepcopy(self.config); config["workspaces"][0]["sections"][0]["enabled"]=False
        projected=visible_workspace_config(config,structure=self.structure,rbac=self.rbac,role_ids=["gestor"]); self.assertEqual(projected["workspaces"],[])
    def test_disabled_item_is_removed_and_home_falls_back(self):
        config=deepcopy(self.config); config["workspaces"][0]["sections"][0]["items"][0]["enabled"]=False
        projected=visible_workspace_config(config,structure=self.structure,rbac=self.rbac,role_ids=["gestor"]); workspace=projected["workspaces"][0]; self.assertEqual([item["id"] for item in workspace["sections"][0]["items"]],["contratos","relatorio"]); self.assertEqual(workspace["home"],"contratos")
    def test_hidden_home_falls_back_to_first_authorized_item(self): self.assertEqual(visible_workspace_config(self.config,structure=self.structure,rbac=self.rbac,role_ids=["fiscal"])["workspaces"][0]["home"],"contratos")
    def test_workspace_without_authorized_destination_is_removed(self):
        config={"version":1,"default_workspace":"fornecedores","workspaces":[{"id":"fornecedores","label":"Fornecedores","home":"lista","sections":[{"id":"principal","label":"Principal","items":[{"id":"lista","label":"Fornecedores","destination":{"kind":"crud","ref":"Fornecedor","operation":"list"}}]}]}]}; projected=visible_workspace_config(config,structure=self.structure,rbac=self.rbac,role_ids=["fiscal"]); self.assertEqual(projected["workspaces"],[]); self.assertEqual(projected["default_workspace"],"")
    def test_default_workspace_falls_back_to_first_visible_workspace(self):
        config={"version":1,"default_workspace":"fornecedores","workspaces":[{"id":"fornecedores","label":"Fornecedores","home":"lista","sections":[{"id":"principal","label":"Principal","items":[{"id":"lista","label":"Fornecedores","destination":{"kind":"crud","ref":"Fornecedor","operation":"list"}}]}]},{"id":"contratos","label":"Contratos","home":"lista","sections":[{"id":"principal","label":"Principal","items":[{"id":"lista","label":"Contratos","destination":{"kind":"crud","ref":"Contrato","operation":"list"}}]}]}]}; self.assertEqual(visible_workspace_config(config,structure=self.structure,rbac=self.rbac,role_ids=["fiscal"])["default_workspace"],"contratos")
