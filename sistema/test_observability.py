import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from sistema.models import Ambiente, ObservabilityEvent, Sistema
from sistema.observability import REDACTED, emit_event, sanitize_context


class ObservabilitySanitizationTests(TestCase):
    def test_sensitive_values_are_redacted_recursively(self):
        payload = {
            "password": "123",
            "Authorization": "Bearer abc",
            "nested": {
                "access-token": "abc",
                "safe": "visible",
                "api_key": "key",
            },
        }
        result = sanitize_context(payload)
        self.assertEqual(result["password"], REDACTED)
        self.assertEqual(result["Authorization"], REDACTED)
        self.assertEqual(result["nested"]["access-token"], REDACTED)
        self.assertEqual(result["nested"]["api_key"], REDACTED)
        self.assertEqual(result["nested"]["safe"], "visible")

    def test_database_url_keeps_location_but_redacts_password(self):
        result = sanitize_context({"DATABASE_URL": "postgresql://alice:supersecret@db:5432/app"})
        self.assertEqual(result["DATABASE_URL"], f"postgresql://alice:{REDACTED}@db:5432/app")
        self.assertNotIn("supersecret", result["DATABASE_URL"])


class ObservabilityEmitterTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="observer", password="test")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Sistema Observável", slug="sistema-observavel")
        self.ambiente = Ambiente.objects.create(
            sistema=self.sistema,
            tipo=Ambiente.TIPO_DEVELOPMENT,
            nome="Development",
        )

    def test_emit_event_persists_structured_event_and_correlation(self):
        correlation_id = uuid.uuid4()
        event = emit_event(
            sistema=self.sistema,
            ambiente=self.ambiente,
            usuario=self.user,
            level=ObservabilityEvent.LEVEL_WARNING,
            category=ObservabilityEvent.CATEGORY_RUNTIME,
            event_name="runtime.check.degraded",
            message="Runtime degradado",
            correlation_id=correlation_id,
            source="runtime_monitor",
            object_type="RuntimeCheck",
            object_id="42",
            context={"latency_ms": 900, "token": "never-store-me"},
        )
        self.assertIsNotNone(event)
        event.refresh_from_db()
        self.assertEqual(event.correlation_id, correlation_id)
        self.assertEqual(event.sistema, self.sistema)
        self.assertEqual(event.ambiente, self.ambiente)
        self.assertEqual(event.usuario, self.user)
        self.assertEqual(event.event_name, "runtime.check.degraded")
        self.assertEqual(event.context["latency_ms"], 900)
        self.assertEqual(event.context["token"], REDACTED)

    def test_emit_event_generates_correlation_id(self):
        event = emit_event(
            sistema=self.sistema,
            event_name="generation.started",
            message="Geração iniciada",
            category=ObservabilityEvent.CATEGORY_GENERATION,
        )
        self.assertIsInstance(event.correlation_id, uuid.UUID)

    def test_invalid_level_and_category_are_rejected_before_persistence(self):
        with self.assertRaises(ValueError):
            emit_event(sistema=self.sistema, event_name="x", message="x", level="INVALID")
        with self.assertRaises(ValueError):
            emit_event(sistema=self.sistema, event_name="x", message="x", category="INVALID")
        self.assertEqual(ObservabilityEvent.objects.count(), 0)

    def test_persistence_failure_does_not_break_primary_operation(self):
        with patch("sistema.observability.ObservabilityEvent.objects.create", side_effect=RuntimeError("db down")):
            with self.assertLogs("sistema.observability", level="ERROR") as captured:
                result = emit_event(
                    sistema=self.sistema,
                    event_name="generation.started",
                    message="Geração iniciada",
                )
        self.assertIsNone(result)
        self.assertTrue(any("Falha ao persistir evento de observabilidade generation.started" in line for line in captured.output))
