import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Ambiente, ObservabilityEvent, Sistema


class MonitoringCenterTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="monitor-owner", password="x")
        self.other = User.objects.create_user(username="monitor-other", password="x")
        self.sistema = Sistema.objects.create(usuario=self.owner, nome="Monitor App")
        self.other_system = Sistema.objects.create(usuario=self.other, nome="Other App")
        self.ambiente = Ambiente.objects.create(sistema=self.sistema, tipo=Ambiente.TIPO_TEST, nome="Test")
        self.correlation_id = uuid.uuid4()
        self.event = ObservabilityEvent.objects.create(
            sistema=self.sistema,
            ambiente=self.ambiente,
            level=ObservabilityEvent.LEVEL_ERROR,
            category=ObservabilityEvent.CATEGORY_RUNTIME,
            source="runtime_agent",
            event_name="runtime.check.offline",
            message="Ambiente indisponível",
            correlation_id=self.correlation_id,
            context={"reason": "offline"},
        )
        ObservabilityEvent.objects.create(
            sistema=self.sistema,
            ambiente=self.ambiente,
            category=ObservabilityEvent.CATEGORY_RUNTIME,
            source="runtime_agent",
            event_name="runtime.check.started",
            message="Verificação iniciada",
            correlation_id=self.correlation_id,
        )
        ObservabilityEvent.objects.create(
            sistema=self.other_system,
            event_name="security.private",
            message="Evento privado de outro sistema",
        )

    def test_monitoring_center_requires_owner(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("sistema:monitoring_center", args=[self.sistema.pk]))
        self.assertEqual(response.status_code, 404)

    def test_monitoring_center_lists_only_owned_system_events(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("sistema:monitoring_center", args=[self.sistema.pk]), {"period": "all"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "runtime.check.offline")
        self.assertNotContains(response, "security.private")

    def test_monitoring_center_filters_level_and_category(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("sistema:monitoring_center", args=[self.sistema.pk]), {
            "period": "all", "level": "ERROR", "category": "RUNTIME"
        })
        self.assertContains(response, "runtime.check.offline")
        self.assertNotContains(response, "runtime.check.started")

    def test_event_detail_shows_correlated_timeline(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("sistema:monitoring_event_detail", args=[self.sistema.pk, self.event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "runtime.check.offline")
        self.assertContains(response, "runtime.check.started")
        self.assertContains(response, str(self.correlation_id))
        self.assertContains(response, '"reason": "offline"')

    def test_event_detail_cannot_cross_system_boundary(self):
        foreign = ObservabilityEvent.objects.filter(sistema=self.other_system).first()
        self.client.force_login(self.owner)
        response = self.client.get(reverse("sistema:monitoring_event_detail", args=[self.sistema.pk, foreign.pk]))
        self.assertEqual(response.status_code, 404)

    def test_workspace_exposes_monitoring_center(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("sistema:workspace", args=[self.sistema.pk]))
        self.assertContains(response, "Logs &amp; Observability")
        self.assertContains(response, reverse("sistema:monitoring_center", args=[self.sistema.pk]))
