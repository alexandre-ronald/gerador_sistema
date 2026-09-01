from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .environment_manager import EnvironmentManagerService
from .models import Ambiente, PromocaoAmbiente, Sistema, VersaoGeracao

User = get_user_model()


class EnvironmentManagerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="env-owner", password="senha-forte")
        self.other = User.objects.create_user(username="env-other", password="senha-forte")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Environment Manager Teste")
        self.client.force_login(self.user)
        self.service = EnvironmentManagerService(self.sistema)

    def _release(self, numero=1, status=VersaoGeracao.STATUS_RELEASED):
        return VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=numero,
            descricao=f"Release v{numero}",
            estrutura_json={"ok": True},
            status=status,
        )

    def test_defaults_create_four_environments_idempotently(self):
        self.service.ensure_defaults()
        self.service.ensure_defaults()
        self.assertEqual(Ambiente.objects.filter(sistema=self.sistema).count(), 4)
        self.assertSetEqual(
            set(Ambiente.objects.filter(sistema=self.sistema).values_list("tipo", flat=True)),
            {"DEVELOPMENT", "TEST", "STAGING", "PRODUCTION"},
        )

    def test_released_version_can_be_promoted(self):
        release = self._release()
        ambiente = self.service.ensure_defaults()[0]
        promocao = self.service.promote(ambiente, release, "Primeira promoção")
        ambiente.refresh_from_db()
        self.assertEqual(ambiente.release_atual, release)
        self.assertEqual(promocao.versao, release)
        self.assertEqual(promocao.observacao, "Primeira promoção")

    def test_non_released_version_cannot_be_promoted(self):
        version = self._release(status=VersaoGeracao.STATUS_VALIDATED)
        ambiente = self.service.ensure_defaults()[0]
        with self.assertRaises(ValidationError):
            self.service.promote(ambiente, version)

    def test_draft_zero_cannot_be_promoted(self):
        draft = VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=0,
            estrutura_json={"dashboard": {}},
            status=VersaoGeracao.STATUS_DRAFT,
        )
        ambiente = self.service.ensure_defaults()[0]
        with self.assertRaises(ValidationError):
            self.service.promote(ambiente, draft)

    def test_cross_system_version_is_blocked(self):
        other_system = Sistema.objects.create(usuario=self.user, nome="Outro Sistema")
        version = VersaoGeracao.objects.create(
            sistema=other_system,
            numero=1,
            estrutura_json={"ok": True},
            status=VersaoGeracao.STATUS_RELEASED,
        )
        ambiente = self.service.ensure_defaults()[0]
        with self.assertRaises(ValidationError):
            self.service.promote(ambiente, version)

    def test_promotion_preserves_history(self):
        ambiente = self.service.ensure_defaults()[0]
        release1 = self._release(1)
        release2 = self._release(2)
        self.service.promote(ambiente, release1)
        self.service.promote(ambiente, release2)
        ambiente.refresh_from_db()
        self.assertEqual(ambiente.release_atual, release2)
        self.assertEqual(PromocaoAmbiente.objects.filter(ambiente=ambiente).count(), 2)

    def test_environment_manager_requires_owner(self):
        url = reverse("sistema:environment_manager", args=[self.sistema.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_environment_page_materializes_defaults(self):
        url = reverse("sistema:environment_manager", args=[self.sistema.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Environment Manager")
        self.assertEqual(Ambiente.objects.filter(sistema=self.sistema).count(), 4)

    def test_promote_view_updates_current_release(self):
        release = self._release()
        ambiente = self.service.ensure_defaults()[0]
        url = reverse("sistema:promote_environment", args=[self.sistema.pk, ambiente.pk])
        response = self.client.post(url, {"version_id": release.pk, "observacao": "via tela"})
        self.assertEqual(response.status_code, 302)
        ambiente.refresh_from_db()
        self.assertEqual(ambiente.release_atual, release)

    def test_released_versions_excludes_draft_and_validated(self):
        released = self._release(1, VersaoGeracao.STATUS_RELEASED)
        self._release(2, VersaoGeracao.STATUS_VALIDATED)
        VersaoGeracao.objects.create(sistema=self.sistema, numero=0, estrutura_json={})
        self.assertEqual(list(self.service.released_versions()), [released])
