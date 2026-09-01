from django.db import models


class RuntimeSnapshot(models.Model):
    ambiente = models.OneToOneField(
        "sistema.Ambiente",
        on_delete=models.CASCADE,
        related_name="runtime_snapshot",
    )
    online = models.BooleanField(default=False)
    contract = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=30, blank=True)
    release_observada = models.CharField(max_length=50, blank=True)
    ambiente_observado = models.CharField(max_length=50, blank=True)
    database_vendor = models.CharField(max_length=50, blank=True)
    migrations_pending = models.PositiveIntegerField(default=0)
    uptime_seconds = models.PositiveBigIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    erro = models.TextField(blank=True)
    verificado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Snapshot de Runtime"
        verbose_name_plural = "Snapshots de Runtime"

    def __str__(self):
        state = "online" if self.online else "offline"
        return f"{self.ambiente} · {state}"
