from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .security_validation import validate_generated_security


class Gen0009SecurityValidationTests(SimpleTestCase):
    def test_clean_project_passes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings.py").write_text("SECRET_KEY = env('SECRET_KEY')\nDEBUG = False\n", encoding="utf-8")
            result = validate_generated_security(root)
            self.assertIn("settings.py", result)

    def test_detects_hardcoded_secret(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings.py").write_text("SECRET_KEY = 'django-insecure-test'\n", encoding="utf-8")
            with self.assertRaises(ValidationError):
                validate_generated_security(root)

    def test_detects_open_debug_and_hosts(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings.py").write_text("DEBUG = True\nALLOWED_HOSTS = ['*']\n", encoding="utf-8")
            with self.assertRaises(ValidationError):
                validate_generated_security(root)
