from django.contrib.auth import get_user_model
from django.test import TestCase

from .application_preview_views import _apply_report_permissions
from .models import Sistema, VersaoGeracao


class ApplicationPreviewReportPermissionTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="report_role_preview", password="x")
        self.sistema = Sistema.objects.create(
            usuario=user,
            nome="Gestão de Contratos",
            slug="gestao-contratos-report-role-preview",
        )
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={
                "rbac": {
                    "enabled": True,
                    "roles": [
                        {"id": "gestor", "label": "Gestor", "group": "Gestor", "order": 0},
                        {"id": "operador", "label": "Operador", "group": "Operador", "order": 1},
                    ],
                    "entities": {},
                    "reports": {
                        "Contrato": {
                            "contratos_geral": ["gestor", "operador"],
                            "contratos_vencendo": ["gestor"],
                        },
                        "Fornecedor": {
                            "fornecedores_geral": ["gestor"],
                        },
                    },
                }
            },
        )

    def _report(self, entity, entity_id, report_id, title):
        return {
            "entity": entity,
            "entity_id": entity_id,
            "id": report_id,
            "title": title,
            "navigation": {"path": [entity], "label": title},
        }

    def _preview(self, role_id="operador", report_page=None):
        reports = [
            self._report("Contrato", 1, "contratos_geral", "Contratos"),
            self._report("Contrato", 1, "contratos_vencendo", "Contratos vencendo"),
            self._report("Fornecedor", 2, "fornecedores_geral", "Fornecedores"),
        ]
        return {
            "role_simulation": {
                "active": True,
                "invalid_role": False,
                "selected_role_id": role_id,
            },
            "page_kind": "report" if report_page else "list",
            "reports": list(reports),
            "entity_reports": list(reports[:2]),
            "report_page": report_page,
            "navigation": {"reports": []},
            "list_page": {"entity": "Contrato"},
            "form_page": None,
            "dashboard_page": None,
            "workflow_page": None,
            "content": {"title": "Contratos", "subtitle": ""},
        }

    def test_operator_sees_only_authorized_reports(self):
        preview = self._preview()
        _apply_report_permissions(self.sistema, preview)

        self.assertEqual([item["id"] for item in preview["reports"]], ["contratos_geral"])
        self.assertEqual([item["id"] for item in preview["entity_reports"]], ["contratos_geral"])
        navigation_ids = [row["id"] for row in preview["navigation"]["reports"] if row["kind"] == "report"]
        self.assertEqual(navigation_ids, ["contratos_geral"])

    def test_direct_access_to_unauthorized_report_is_blocked(self):
        denied = self._report("Fornecedor", 2, "fornecedores_geral", "Fornecedores")
        preview = self._preview(report_page=denied)
        _apply_report_permissions(self.sistema, preview)

        self.assertIsNone(preview["report_page"])
        self.assertEqual(preview["report_access_denied"]["id"], "fornecedores_geral")
        self.assertIsNone(preview["list_page"])
        self.assertEqual(preview["content"]["title"], "Relatório não disponível para este papel")

    def test_manager_keeps_reports_granted_to_manager(self):
        allowed = self._report("Fornecedor", 2, "fornecedores_geral", "Fornecedores")
        preview = self._preview(role_id="gestor", report_page=allowed)
        _apply_report_permissions(self.sistema, preview)

        self.assertEqual(len(preview["reports"]), 3)
        self.assertEqual(preview["report_page"]["id"], "fornecedores_geral")
        self.assertNotIn("report_access_denied", preview)

    def test_invalid_role_is_fail_closed_for_reports(self):
        preview = self._preview()
        preview["role_simulation"] = {
            "active": False,
            "invalid_role": True,
            "selected_role_id": "",
        }
        _apply_report_permissions(self.sistema, preview)
        self.assertEqual(preview["reports"], [])
        self.assertEqual(preview["entity_reports"], [])

    def test_legacy_rbac_without_report_contract_keeps_legacy_visibility(self):
        draft = VersaoGeracao.objects.get(sistema=self.sistema, numero=0)
        structure = draft.estrutura_json
        structure["rbac"].pop("reports")
        draft.estrutura_json = structure
        draft.save(update_fields=["estrutura_json"])

        preview = self._preview()
        _apply_report_permissions(self.sistema, preview)
        self.assertEqual(len(preview["reports"]), 3)
