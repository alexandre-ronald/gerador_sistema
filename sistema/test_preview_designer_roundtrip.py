from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase
from django.template.loader import render_to_string
from django.urls import resolve, reverse


class PreviewDesignerRoundTripTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.sistema = SimpleNamespace(id=17)

    def render_header(self, route_name, query=None):
        path = reverse(f"sistema:{route_name}", args=[self.sistema.id])
        request = self.factory.get(path, query or {})
        request.resolver_match = resolve(path)
        return render_to_string(
            "sistema/_page_header.html",
            {
                "request": request,
                "sistema": self.sistema,
                "title": "Designer",
                "subtitle": "Teste",
            },
        )

    def test_crud_returns_to_same_entity_list_preview(self):
        html = self.render_header("crud_designer", {"entidade": "42"})
        preview = reverse("sistema:application_preview", args=[self.sistema.id])
        self.assertIn(f'{preview}?entidade=42', html)
        self.assertIn('data-designer-preview-link', html)

    def test_form_returns_to_same_entity_form_preview(self):
        html = self.render_header("form_designer", {"entidade": "42"})
        preview = reverse("sistema:application_preview", args=[self.sistema.id])
        self.assertIn(f'{preview}?pagina=form&entidade=42', html)

    def test_workflow_returns_to_same_entity_workflow_preview(self):
        html = self.render_header("workflow_designer", {"entidade": "42"})
        preview = reverse("sistema:application_preview", args=[self.sistema.id])
        self.assertIn(f'{preview}?pagina=workflow&entidade=42', html)

    def test_report_returns_to_same_entity_report_preview(self):
        html = self.render_header("report_designer", {"entidade": "42"})
        preview = reverse("sistema:application_preview", args=[self.sistema.id])
        self.assertIn(f'{preview}?pagina=report&entidade=42', html)

    def test_dashboard_returns_to_dashboard_preview(self):
        html = self.render_header("dashboard_builder")
        preview = reverse("sistema:application_preview", args=[self.sistema.id])
        self.assertIn(f'{preview}?pagina=dashboard', html)

    def test_permission_returns_to_full_preview(self):
        html = self.render_header("permission_designer")
        preview = reverse("sistema:application_preview", args=[self.sistema.id])
        self.assertIn(f'href="{preview}"', html)
