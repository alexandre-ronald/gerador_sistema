from pathlib import Path

from django.test import SimpleTestCase
from django.urls import resolve


class GenerationPipelineRegressionTests(SimpleTestCase):
    def test_generation_route_uses_canonical_pipeline(self):
        match = resolve("/gerar/1/processar/")
        self.assertEqual(match.url_name, "processar_geracao_ajax")
        self.assertEqual(match.func.__module__, "sistema.geracao")

    def test_legacy_installer_injection_is_not_part_of_canonical_pipeline(self):
        content = (
            Path(__file__).resolve().parent / "geracao.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Salvador:", content)
        self.assertIn("GeradorService(pk)", content)
        self.assertNotIn("conteudo_bat", content)

    def test_installer_template_is_the_single_materialized_source(self):
        content = (
            Path(__file__).resolve().parent
            / "templates"
            / "gerador"
            / "snippets"
            / "instalacao.txt"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Salvador:", content)
        self.assertIn("python -m pip install -r requirements.txt", content)
        self.assertIn("call .venv\\Scripts\\activate.bat", content)
        self.assertIn("python manage.py check", content)
