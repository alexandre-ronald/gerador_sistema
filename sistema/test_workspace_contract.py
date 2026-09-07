from django.test import SimpleTestCase
from .workspace_contract import WorkspaceContractError,default_workspace_config,normalize_workspace_config,workspace_item_map,workspace_map

class WorkspaceContractTests(SimpleTestCase):
    def _config(self):
        return {"version":1,"default_workspace":"gestao_fornecedores","workspaces":[{"id":"gestao_fornecedores","label":"Gestão de Fornecedores","description":"Operação de fornecedores e contratos","home":"fornecedores","sections":[{"id":"operacao","label":"Operação","items":[{"id":"fornecedores","label":"Fornecedores","destination":{"kind":"crud","ref":"Fornecedor","operation":"list"}},{"id":"central_fornecedor","label":"Central do Fornecedor","destination":{"kind":"advanced_page","ref":"central_fornecedor"}}]}]},{"id":"fiscalizacao","label":"Fiscalização","home":"contratos","sections":[{"id":"contratos_secao","label":"Contratos","items":[{"id":"contratos","label":"Contratos","destination":{"kind":"crud","ref":"Contrato","operation":"list"}}]}]}]}
    def test_default_contract_is_empty_and_versioned(self): self.assertEqual(default_workspace_config(),{"version":1,"default_workspace":"","workspaces":[]})
    def test_normalizes_multiple_workspaces_and_default(self):
        config=normalize_workspace_config(self._config()); self.assertEqual(config["default_workspace"],"gestao_fornecedores"); self.assertEqual([w["id"] for w in config["workspaces"]],["gestao_fornecedores","fiscalizacao"]); self.assertEqual(config["workspaces"][0]["home"],"fornecedores")
    def test_normalizes_stable_destination_references(self): self.assertEqual(normalize_workspace_config(self._config())["workspaces"][0]["sections"][0]["items"][0]["destination"],{"kind":"crud","ref":"Fornecedor","operation":"list"})
    def test_normalizes_workflow_destination_by_entity(self):
        raw=self._config(); raw["workspaces"][0]["sections"][0]["items"].append({"id":"fluxo_contrato","label":"Fluxo de Contratos","destination":{"kind":"workflow","ref":"Contrato"}}); config=normalize_workspace_config(raw); self.assertEqual(config["workspaces"][0]["sections"][0]["items"][-1]["destination"],{"kind":"workflow","ref":"Contrato"})
    def test_rejects_unknown_workspace_home(self):
        raw=self._config(); raw["workspaces"][0]["home"]="nao_existe"
        with self.assertRaises(WorkspaceContractError) as error: normalize_workspace_config(raw)
        self.assertEqual(error.exception.code,"unknown_workspace_home")
    def test_rejects_unknown_default_workspace(self):
        raw=self._config(); raw["default_workspace"]="nao_existe"
        with self.assertRaises(WorkspaceContractError) as error: normalize_workspace_config(raw)
        self.assertEqual(error.exception.code,"unknown_default_workspace")
    def test_rejects_duplicate_workspace_ids(self):
        raw=self._config(); raw["workspaces"][1]["id"]="gestao_fornecedores"
        with self.assertRaises(WorkspaceContractError) as error: normalize_workspace_config(raw)
        self.assertEqual(error.exception.code,"duplicate_workspace_id")
    def test_rejects_duplicate_item_ids_inside_same_workspace(self):
        raw=self._config(); raw["workspaces"][0]["sections"].append({"id":"outra","label":"Outra","items":[{"id":"fornecedores","label":"Duplicado","destination":{"kind":"report","ref":"contratos"}}]})
        with self.assertRaises(WorkspaceContractError) as error: normalize_workspace_config(raw)
        self.assertEqual(error.exception.code,"duplicate_workspace_item_id")
    def test_same_item_id_may_exist_in_different_workspaces(self):
        raw=self._config(); raw["workspaces"][1]["sections"][0]["items"][0]["id"]="fornecedores"; raw["workspaces"][1]["home"]="fornecedores"; self.assertEqual(normalize_workspace_config(raw)["workspaces"][1]["home"],"fornecedores")
    def test_rejects_unknown_destination_kind(self):
        raw=self._config(); raw["workspaces"][0]["sections"][0]["items"][0]["destination"]["kind"]="url"
        with self.assertRaises(WorkspaceContractError) as error: normalize_workspace_config(raw)
        self.assertEqual(error.exception.code,"unknown_destination_kind")
    def test_non_strict_discards_invalid_workspace_and_invalid_default(self):
        raw=self._config(); raw["workspaces"].append({"id":"quebrado","label":"","sections":[]}); raw["default_workspace"]="quebrado"; normalized=normalize_workspace_config(raw,strict=False); self.assertEqual(len(normalized["workspaces"]),2); self.assertEqual(normalized["default_workspace"],"")
    def test_workspace_maps_use_stable_ids(self):
        workspaces=workspace_map(self._config()); self.assertEqual(set(workspaces),{"gestao_fornecedores","fiscalizacao"}); items=workspace_item_map(self._config(),"gestao_fornecedores"); self.assertEqual(set(items),{"fornecedores","central_fornecedor"})
