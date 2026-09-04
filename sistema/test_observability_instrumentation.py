from django.contrib.auth import get_user_model
from django.test import TestCase

from sistema.models import ObservabilityEvent, Sistema, VersaoGeracao
from sistema.release_manager import ReleaseManagerService
from sistema.validation_center import validate_system


class ValidationObservabilityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="validation-observer", password="test")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema Observabilidade Validação",
            slug="sistema-observabilidade-validacao",
        )

    def test_validation_emits_correlated_start_and_completion_events(self):
        report = validate_system(self.sistema)

        self.assertIn(report["overall_status"], {"warning", "pending"})
        events = list(
            ObservabilityEvent.objects.filter(
                sistema=self.sistema,
                category=ObservabilityEvent.CATEGORY_VALIDATION,
            ).order_by("created_at", "id")
        )
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_name, "validation.started")
        self.assertEqual(events[1].event_name, "validation.completed")
        self.assertEqual(events[0].correlation_id, events[1].correlation_id)
        self.assertEqual(events[1].context["overall_status"], report["overall_status"])
        self.assertEqual(events[1].context["release_ready"], report["release_ready"])


class ReleaseObservabilityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="release-observer", password="test")
        self.sistema = Sistema.objects.create(
            usuario=self.user,
            nome="Sistema Observabilidade Release",
            slug="sistema-observabilidade-release",
        )
        self.version = VersaoGeracao.objects.create(
            sistema=self.sistema,
            numero=1,
            descricao="Release candidata",
            estrutura_json={"modules": []},
            status=VersaoGeracao.STATUS_VALIDATED,
        )

    def test_release_publish_emits_structured_event(self):
        released = ReleaseManagerService(self.sistema).release(self.version, changelog="Primeira release")

        self.assertEqual(released.status, VersaoGeracao.STATUS_RELEASED)
        event = ObservabilityEvent.objects.get(
            sistema=self.sistema,
            event_name="release.published",
        )
        self.assertEqual(event.category, ObservabilityEvent.CATEGORY_RELEASE)
        self.assertEqual(event.source, "release_manager")
        self.assertEqual(event.object_type, "VersaoGeracao")
        self.assertEqual(event.object_id, str(self.version.pk))
        self.assertEqual(event.context["version"], 1)
        self.assertTrue(event.context["has_changelog"])
