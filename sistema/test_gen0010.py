from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .integration_validation import validate_generated_integration


class Gen0010IntegrationValidationTests(SimpleTestCase):
    def test_valid_project_passes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "views.py").write_text(
                "from django.shortcuts import render\ndef home(request):\n    return render(request, 'app/home.html')\n",
                encoding="utf-8",
            )
            (root / "app" / "templates" / "app").mkdir(parents=True)
            (root / "app" / "templates" / "app" / "home.html").write_text("{% extends 'base.html' %}", encoding="utf-8")
            result = validate_generated_integration(root)
            self.assertIn("views.py", result)

    def test_missing_template_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "views.py").write_text(
                "from django.shortcuts import render\ndef home(request):\n    return render(request, 'app/missing.html')\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValidationError):
                validate_generated_integration(root)

    def test_invalid_python_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "views.py").write_text("def broken(:\n", encoding="utf-8")
            with self.assertRaises(ValidationError):
                validate_generated_integration(root)
