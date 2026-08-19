from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase

from .compiler import SpecificationCompiler
from .models import Entidade, Modulo, Sistema
from .specification import build_specification


class Gen0012CrudAdvancedTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="gen0012", password="secret123")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Sistema CRUD GEN-0012")
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Cadastro")
        Entidade.objects.create(modulo=modulo, nome="Pessoa", gerar_crud_views=True)

    def test_plan_contains_detail_template(self):
        spec = build_specification(self.sistema)
        paths = SpecificationCompiler(spec).plan.paths()
        self.assertIn("cadastro/templates/cadastro/pessoa_detail.html", paths)

    def test_generated_views_include_detail_view(self):
        spec = build_specification(self.sistema)
        compiled = SpecificationCompiler(spec).compile()
        views = next(item.content for item in compiled if item.path == "cadastro/views.py")
        self.assertIn("DetailView", views)
        self.assertIn("PessoaDetailView", views)
        self.assertIn('pessoa_detail.html', views)

    def test_generated_urls_include_detail_route(self):
        spec = build_specification(self.sistema)
        compiled = SpecificationCompiler(spec).compile()
        urls = next(item.content for item in compiled if item.path == "cadastro/urls.py")
        self.assertIn('name="pessoa_detail"', urls)
        self.assertIn('PessoaDetailView.as_view()', urls)

    def test_generated_detail_template_is_materialized(self):
        spec = build_specification(self.sistema)
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "project"
            SpecificationCompiler(spec).write(output)
            detail = output / "cadastro/templates/cadastro/pessoa_detail.html"
            self.assertTrue(detail.exists())
            self.assertIn("Editar", detail.read_text(encoding="utf-8"))
            self.assertIn("Excluir", detail.read_text(encoding="utf-8"))
