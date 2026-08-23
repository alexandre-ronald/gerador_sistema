import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sistema.installer_views import _estrutura_snapshot
from sistema.models import Modulo, Sistema, VersaoGeracao


class GenerationVersioningTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="teste", password="senha123")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema de Eleição",
            caminho_geracao=tempfile.mkdtemp(prefix="preview_"),
        )

    def test_version_numbers_are_unique_per_system(self):
        VersaoGeracao.objects.create(sistema=self.sistema, numero=1, estrutura_json={"ok": True})
        with self.assertRaises(Exception):
            VersaoGeracao.objects.create(sistema=self.sistema, numero=1, estrutura_json={"ok": False})

    def test_snapshot_preserves_display_names_with_accents(self):
        modulo = Modulo.objects.create(sistema=self.sistema, nome="Gestão de Pessoas")
        estrutura = _estrutura_snapshot(self.sistema)
        self.assertEqual(estrutura["sistema"]["nome"], "Sistema de Eleição")
        self.assertEqual(estrutura["modulos"][0]["nome"], "Gestão de Pessoas")

    def test_preview_returns_last_version_and_generated_files(self):
        root = Path(self.sistema.caminho_geracao)
        (root / "manage.py").write_text("# teste", encoding="utf-8")
        (root / "__pycache__").mkdir()
        (root / "__pycache__" / "ignore.pyc").write_bytes(b"x")
        VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=1,
            estrutura_json={"sistema": {"nome": self.sistema.nome}},
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("sistema:preview_geracao", kwargs={"pk": self.sistema.pk}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["versao"], 1)
        self.assertIn("manage.py", data["arquivos"])
        self.assertNotIn("__pycache__/ignore.pyc", data["arquivos"])
