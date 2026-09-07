from django.test import SimpleTestCase

from .workspace_semantics import WorkspaceSemanticError, validate_workspace_destinations


class WorkspaceSemanticTests(SimpleTestCase):
    def _structure(self):
        return {
            "cruds": {"Fornecedor": {}, "Contrato": {}},
            "dashboard": {"enabled": True, "title": "Dashboard"},
            "reports": {
                "Contrato": [
                    {"id": "contratos_ativos", "enabled": True},
                    {"id": "contratos_inativos", "enabled": False},
                ]
            },
            "advanced_pages": {
                "version": 1,
                "pages": [
                    {"id": "central_fornecedor", "name": "Central do Fornecedor", "slug": "fornecedores/central", "enabled": True, "context": {"kind": "none"}, "navigation": {}, "components": [], "actions": []},
                    {"id": "pagina_oculta", "name": "Oculta", "slug": "oculta", "enabled": False, "context": {"kind": "none"}, "navigation": {}, "components": [], "actions": []},
                ],
            },
        }

    def _config(self, destination):
        return {
            "version": 1,
            "default_workspace": "operacao",
            "workspaces": [
                {
                    "id": "operacao",
                    "label": "Operação",
                    "home": "entrada",
                    "sections": [
                        {"id": "principal", "label": "Principal", "items": [{"id": "entrada", "label": "Entrada", "destination": destination}]}
                    ],
                }
            ],
        }

    def test_accepts_existing_enabled_advanced_page(self):
        config = validate_workspace_destinations(self._config({"kind": "advanced_page", "ref": "central_fornecedor"}), self._structure(), entities=[{"name": "Fornecedor"}, {"name": "Contrato"}])
        self.assertEqual(config["workspaces"][0]["home"], "entrada")

    def test_rejects_disabled_advanced_page_fail_closed(self):
        with self.assertRaises(WorkspaceSemanticError) as error:
            validate_workspace_destinations(self._config({"kind": "advanced_page", "ref": "pagina_oculta"}), self._structure(), entities=["Fornecedor", "Contrato"])
        self.assertEqual(error.exception.code, "workspace_destination_not_found")

    def test_accepts_existing_crud_list(self):
        validate_workspace_destinations(self._config({"kind": "crud", "ref": "Fornecedor", "operation": "list"}), self._structure(), entities=["Fornecedor", "Contrato"])

    def test_rejects_crud_for_unknown_entity(self):
        with self.assertRaises(WorkspaceSemanticError) as error:
            validate_workspace_destinations(self._config({"kind": "crud", "ref": "Paciente", "operation": "list"}), self._structure(), entities=["Fornecedor", "Contrato"])
        self.assertEqual(error.exception.code, "workspace_destination_not_found")

    def test_rejects_non_navigable_crud_operation(self):
        with self.assertRaises(WorkspaceSemanticError) as error:
            validate_workspace_destinations(self._config({"kind": "crud", "ref": "Fornecedor", "operation": "delete"}), self._structure(), entities=["Fornecedor", "Contrato"])
        self.assertEqual(error.exception.code, "workspace_destination_not_navigable")

    def test_accepts_enabled_dashboard_by_canonical_ref(self):
        validate_workspace_destinations(self._config({"kind": "dashboard", "ref": "dashboard"}), self._structure(), entities=[])

    def test_rejects_dashboard_when_disabled(self):
        structure = self._structure(); structure["dashboard"]["enabled"] = False
        with self.assertRaises(WorkspaceSemanticError) as error:
            validate_workspace_destinations(self._config({"kind": "dashboard", "ref": "dashboard"}), structure, entities=[])
        self.assertEqual(error.exception.code, "workspace_destination_not_found")

    def test_accepts_enabled_report(self):
        validate_workspace_destinations(self._config({"kind": "report", "ref": "Contrato:contratos_ativos"}), self._structure(), entities=[])

    def test_rejects_disabled_report(self):
        with self.assertRaises(WorkspaceSemanticError) as error:
            validate_workspace_destinations(self._config({"kind": "report", "ref": "Contrato:contratos_inativos"}), self._structure(), entities=[])
        self.assertEqual(error.exception.code, "workspace_destination_not_found")

    def test_error_preserves_workspace_section_and_item_context(self):
        with self.assertRaises(WorkspaceSemanticError) as error:
            validate_workspace_destinations(self._config({"kind": "report", "ref": "inexistente"}), self._structure(), entities=[])
        self.assertEqual(error.exception.as_dict()["workspace_id"], "operacao")
        self.assertEqual(error.exception.as_dict()["section_id"], "principal")
        self.assertEqual(error.exception.as_dict()["item_id"], "entrada")
