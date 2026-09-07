from django.test import SimpleTestCase

from .workspace_contract import (
    WorkspaceContractError,
    default_workspace_config,
    normalize_workspace_config,
    workspace_item_map,
)


class WorkspaceContractTests(SimpleTestCase):
    def _config(self):
        return {
            "version": 1,
            "home": "fornecedores",
            "sections": [
                {
                    "id": "operacao",
                    "label": "Operação",
                    "order": 10,
                    "items": [
                        {
                            "id": "fornecedores",
                            "label": "Fornecedores",
                            "destination": {"kind": "crud", "ref": "Fornecedor", "operation": "list"},
                        },
                        {
                            "id": "central_fornecedor",
                            "label": "Central do Fornecedor",
                            "destination": {"kind": "advanced_page", "ref": "central_fornecedor"},
                        },
                    ],
                },
                {
                    "id": "acompanhamento",
                    "label": "Acompanhamento",
                    "items": [
                        {
                            "id": "dashboard_compras",
                            "label": "Dashboard",
                            "destination": {"kind": "dashboard", "ref": "compras"},
                        }
                    ],
                },
            ],
        }

    def test_default_contract_is_empty_and_versioned(self):
        self.assertEqual(default_workspace_config(), {"version": 1, "home": "", "sections": []})

    def test_normalizes_workspace_with_stable_destination_references(self):
        config = normalize_workspace_config(self._config())
        self.assertEqual(config["home"], "fornecedores")
        self.assertEqual(config["sections"][0]["items"][0]["destination"], {"kind": "crud", "ref": "Fornecedor", "operation": "list"})
        self.assertEqual(config["sections"][0]["items"][1]["destination"], {"kind": "advanced_page", "ref": "central_fornecedor"})

    def test_rejects_unknown_home(self):
        raw = self._config()
        raw["home"] = "nao_existe"
        with self.assertRaises(WorkspaceContractError) as error:
            normalize_workspace_config(raw)
        self.assertEqual(error.exception.code, "unknown_workspace_home")

    def test_rejects_duplicate_item_ids_across_sections(self):
        raw = self._config()
        raw["sections"][1]["items"][0]["id"] = "fornecedores"
        with self.assertRaises(WorkspaceContractError) as error:
            normalize_workspace_config(raw)
        self.assertEqual(error.exception.code, "duplicate_workspace_item_id")

    def test_rejects_unknown_destination_kind(self):
        raw = self._config()
        raw["sections"][0]["items"][0]["destination"]["kind"] = "url"
        with self.assertRaises(WorkspaceContractError) as error:
            normalize_workspace_config(raw)
        self.assertEqual(error.exception.code, "unknown_destination_kind")

    def test_non_strict_discards_invalid_section_and_invalid_home(self):
        raw = self._config()
        raw["sections"].append({"id": "quebrada", "label": "", "items": []})
        raw["home"] = "quebrada"
        normalized = normalize_workspace_config(raw, strict=False)
        self.assertEqual(len(normalized["sections"]), 2)
        self.assertEqual(normalized["home"], "")

    def test_workspace_item_map_indexes_items_by_stable_id(self):
        items = workspace_item_map(self._config())
        self.assertEqual(set(items), {"fornecedores", "central_fornecedor", "dashboard_compras"})
        self.assertEqual(items["central_fornecedor"]["destination"]["ref"], "central_fornecedor")
