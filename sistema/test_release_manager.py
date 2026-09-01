import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Campo, Entidade, Modulo, Sistema, VersaoGeracao
from .release_manager import ReleaseManagerService


class ReleaseManagerTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="release-owner", password="senha-forte")
        self.other = User.objects.create_user(username="release-other", password="senha-forte")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Release Manager Teste")
        self.client.force_login(self.user)
        modulo = Modulo.objects.create(sistema=self.sistema, nome="cadastro")
        entidade = Entidade.objects.create(modulo=modulo, nome="Pessoa")
        Campo.objects.create(entidade=entidade, nome="nome", tipo="CharField", max_length=120)

    def _version(self, numero=1, status=VersaoGeracao.STATUS_DRAFT, valid=True):
        dashboard = {
            "enabled": True,
            "widgets": [{"type": "metric", "x": 0, "y": 0, "w": 4, "h": 3}],
        }
        if not valid:
            dashboard["widgets"][0].update({"x": 10, "w": 4})
        return VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=numero,
            status=status,
            estrutura_json={"dashboard": dashboard, "modules": []},
            arquivo_zip="sistemas_versoes/teste.zip",
        )

    def test_version_defaults_to_draft(self):
        version = VersaoGeracao.objects.create(sistema=self.sistema, numero=1, estrutura_json={})
        self.assertEqual(version.status, VersaoGeracao.STATUS_DRAFT)

    def test_draft_zero_cannot_be_released(self):
        draft = VersaoGeracao.objects.create(sistema=self.sistema, numero=0, status=VersaoGeracao.STATUS_VALIDATED)
        with self.assertRaises(ValidationError):
            ReleaseManagerService(self.sistema).release(draft)

    def test_unvalidated_version_cannot_be_released(self):
        version = self._version()
        with self.assertRaises(ValidationError):
            ReleaseManagerService(self.sistema).release(version)

    def test_valid_version_passes_quality_gate(self):
        version = self._version()
        report = ReleaseManagerService(self.sistema).validate_version(version)
        version.refresh_from_db()
        self.assertTrue(report["release_ready"])
        self.assertEqual(version.status, VersaoGeracao.STATUS_VALIDATED)
        self.assertIsNotNone(version.validado_em)

    def test_invalid_version_returns_to_draft(self):
        version = self._version(valid=False)
        report = ReleaseManagerService(self.sistema).validate_version(version)
        version.refresh_from_db()
        self.assertFalse(report["release_ready"])
        self.assertEqual(version.status, VersaoGeracao.STATUS_DRAFT)
        self.assertIsNone(version.validado_em)

    def test_validated_version_can_be_released_with_changelog(self):
        version = self._version(status=VersaoGeracao.STATUS_VALIDATED)
        released = ReleaseManagerService(self.sistema).release(version, "Primeira release estável")
        self.assertEqual(released.status, VersaoGeracao.STATUS_RELEASED)
        self.assertEqual(released.changelog, "Primeira release estável")
        self.assertIsNotNone(released.publicado_em)

    def test_release_manager_requires_owner(self):
        version = self._version()
        response = self.client.get(reverse("sistema:release_manager", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Release Manager")
        self.assertContains(response, f"v{version.numero}")
        self.client.force_login(self.other)
        response = self.client.get(reverse("sistema:release_manager", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 404)

    def test_release_manager_hides_draft_zero_from_version_history(self):
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, descricao="Dashboard draft")
        version = self._version(numero=1)
        response = self.client.get(reverse("sistema:release_manager", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 200)
        versions = response.context["versions"]
        self.assertEqual([item.numero for item in versions], [version.numero])

    def test_generation_service_creates_single_numbered_version(self):
        from .services import GeradorService

        with tempfile.TemporaryDirectory() as directory:
            self.sistema.caminho_geracao = directory
            self.sistema.save(update_fields=["caminho_geracao"])
            GeradorService(self.sistema.pk).gerar_projeto_completo()
            self.assertEqual(self.sistema.versoes.filter(numero__gt=0).count(), 1)
