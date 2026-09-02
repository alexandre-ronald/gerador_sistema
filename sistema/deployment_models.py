from django.conf import settings
from django.db import models


class DeploymentPlan(models.Model):
    STATUS_PLANNED = "PLANNED"
    STATUS_VALIDATING = "VALIDATING"
    STATUS_READY = "READY"
    STATUS_RUNNING = "RUNNING"
    STATUS_VERIFYING = "VERIFYING"
    STATUS_SUCCEEDED = "SUCCEEDED"
    STATUS_FAILED = "FAILED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_PLANNED, "Planejado"),
        (STATUS_VALIDATING, "Validando"),
        (STATUS_READY, "Pronto"),
        (STATUS_RUNNING, "Executando"),
        (STATUS_VERIFYING, "Verificando"),
        (STATUS_SUCCEEDED, "Concluído"),
        (STATUS_FAILED, "Falhou"),
        (STATUS_CANCELLED, "Cancelado"),
    ]

    sistema = models.ForeignKey("sistema.Sistema", on_delete=models.CASCADE, related_name="deployment_plans")
    ambiente = models.ForeignKey("sistema.Ambiente", on_delete=models.PROTECT, related_name="deployment_plans")
    versao = models.ForeignKey("sistema.VersaoGeracao", on_delete=models.PROTECT, related_name="deployment_plans")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="deployment_plans")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    executor = models.CharField(max_length=20)
    strategy = models.CharField(max_length=30)
    config_snapshot = models.JSONField(default=dict)
    release_observada = models.CharField(max_length=50, blank=True)
    erro = models.TextField(blank=True)
    etapas = models.JSONField(default=list, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    iniciado_em = models.DateTimeField(null=True, blank=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em", "-id"]
        verbose_name = "Plano de Deployment"
        verbose_name_plural = "Planos de Deployment"

    def __str__(self):
        return f"{self.sistema.nome} · {self.ambiente.nome} · v{self.versao.numero} · {self.status}"
