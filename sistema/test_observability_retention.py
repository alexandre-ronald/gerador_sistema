from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import ObservabilityEvent, Sistema
from .observability_retention import purge_observability_events, retention_policy, retention_preview


class ObservabilityRetentionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="retention-owner", password="x")
        self.sistema = Sistema.objects.create(usuario=self.user, nome="Retention App")
        self.other_system = Sistema.objects.create(usuario=self.user, nome="Retention Other")
        self.now = timezone.now()

    def _event(self, *, level, age_days, sistema=None, name="retention.event"):
        event = ObservabilityEvent.objects.create(
            sistema=sistema or self.sistema,
            level=level,
            event_name=name,
            message="retention",
        )
        ObservabilityEvent.objects.filter(pk=event.pk).update(created_at=self.now - timedelta(days=age_days))
        event.refresh_from_db()
        return event

    def test_default_policy_keeps_more_severe_events_longer(self):
        policy = retention_policy()
        self.assertLess(policy[ObservabilityEvent.LEVEL_DEBUG], policy[ObservabilityEvent.LEVEL_INFO])
        self.assertLess(policy[ObservabilityEvent.LEVEL_INFO], policy[ObservabilityEvent.LEVEL_WARNING])
        self.assertLess(policy[ObservabilityEvent.LEVEL_WARNING], policy[ObservabilityEvent.LEVEL_ERROR])
        self.assertLess(policy[ObservabilityEvent.LEVEL_ERROR], policy[ObservabilityEvent.LEVEL_CRITICAL])

    @override_settings(DJANGOFORGE_OBSERVABILITY_RETENTION_DAYS={"INFO": 45, "ERROR": 270})
    def test_policy_can_be_overridden_from_settings(self):
        policy = retention_policy()
        self.assertEqual(policy[ObservabilityEvent.LEVEL_INFO], 45)
        self.assertEqual(policy[ObservabilityEvent.LEVEL_ERROR], 270)

    def test_preview_does_not_delete_anything(self):
        expired = self._event(level=ObservabilityEvent.LEVEL_INFO, age_days=31)
        result = retention_preview(sistema_id=self.sistema.pk, now=self.now)
        self.assertEqual(result["total"], 1)
        self.assertTrue(ObservabilityEvent.objects.filter(pk=expired.pk).exists())

    def test_apply_deletes_only_expired_events_for_requested_system(self):
        expired_info = self._event(level=ObservabilityEvent.LEVEL_INFO, age_days=31)
        recent_info = self._event(level=ObservabilityEvent.LEVEL_INFO, age_days=10, name="recent")
        old_critical = self._event(level=ObservabilityEvent.LEVEL_CRITICAL, age_days=200, name="critical")
        foreign_expired = self._event(
            level=ObservabilityEvent.LEVEL_INFO,
            age_days=60,
            sistema=self.other_system,
            name="foreign",
        )

        result = purge_observability_events(sistema_id=self.sistema.pk, apply=True, now=self.now)

        self.assertTrue(result["applied"])
        self.assertEqual(result["deleted"], 1)
        self.assertFalse(ObservabilityEvent.objects.filter(pk=expired_info.pk).exists())
        self.assertTrue(ObservabilityEvent.objects.filter(pk=recent_info.pk).exists())
        self.assertTrue(ObservabilityEvent.objects.filter(pk=old_critical.pk).exists())
        self.assertTrue(ObservabilityEvent.objects.filter(pk=foreign_expired.pk).exists())

    def test_management_command_is_safe_by_default(self):
        expired = self._event(level=ObservabilityEvent.LEVEL_DEBUG, age_days=20)
        call_command("observability_retention")
        self.assertTrue(ObservabilityEvent.objects.filter(pk=expired.pk).exists())

    def test_management_command_apply_removes_expired_records(self):
        expired = self._event(level=ObservabilityEvent.LEVEL_DEBUG, age_days=20)
        call_command("observability_retention", "--apply", "--system-id", str(self.sistema.pk))
        self.assertFalse(ObservabilityEvent.objects.filter(pk=expired.pk).exists())
