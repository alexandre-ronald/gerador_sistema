import uuid

from django.conf import settings
from django.db import models


class ObservabilityEvent(models.Model):
    LEVEL_DEBUG = "DEBUG"
    LEVEL_INFO = "INFO"
    LEVEL_WARNING = "WARNING"
    LEVEL_ERROR = "ERROR"
    LEVEL_CRITICAL = "CRITICAL"
    LEVEL_CHOICES = [
        (LEVEL_DEBUG, "Debug"),
        (LEVEL_INFO, "Info"),
        (LEVEL_WARNING, "Warning"),
        (LEVEL_ERROR, "Error"),
        (LEVEL_CRITICAL, "Critical"),
    ]

    CATEGORY_SYSTEM = "SYSTEM"
    CATEGORY_GENERATION = "GENERATION"
    CATEGORY_VALIDATION = "VALIDATION"
    CATEGORY_RELEASE = "RELEASE"
    CATEGORY_DEPLOYMENT = "DEPLOYMENT"
    CATEGORY_RUNTIME = "RUNTIME"
    CATEGORY_SECURITY = "SECURITY"
    CATEGORY_INTEGRATION = "INTEGRATION"
    CATEGORY_CHOICES = [
        (CATEGORY_SYSTEM, "Sistema"),
        (CATEGORY_GENERATION, "Geração"),
        (CATEGORY_VALIDATION, "Validação"),
        (CATEGORY_RELEASE, "Release"),
        (CATEGORY_DEPLOYMENT, "Deployment"),
        (CATEGORY_RUNTIME, "Runtime"),
        (CATEGORY_SECURITY, "Segurança"),
        (CATEGORY_INTEGRATION, "Integração"),
    ]

    sistema = models.ForeignKey(
        "sistema.Sistema",
        on_delete=models.CASCADE,
        related_name="observability_events",
    )
    ambiente = models.ForeignKey(
        "sistema.Ambiente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="observability_events",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="observability_events",
    )
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_SYSTEM)
    source = models.CharField(max_length=100, blank=True)
    event_name = models.CharField(max_length=120)
    message = models.TextField()
    correlation_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Evento de Observabilidade"
        verbose_name_plural = "Eventos de Observabilidade"
        indexes = [
            models.Index(fields=["sistema", "created_at"], name="obs_system_created_idx"),
            models.Index(fields=["sistema", "level", "created_at"], name="obs_system_level_idx"),
            models.Index(fields=["ambiente", "created_at"], name="obs_env_created_idx"),
            models.Index(fields=["category", "created_at"], name="obs_category_created_idx"),
            models.Index(fields=["event_name", "created_at"], name="obs_event_created_idx"),
        ]

    def __str__(self):
        return f"{self.level} · {self.event_name} · {self.created_at:%d/%m/%Y %H:%M:%S}"
