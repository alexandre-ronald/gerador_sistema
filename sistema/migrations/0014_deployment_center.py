from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("sistema", "0013_health_monitoring"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeploymentPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("PLANNED", "Planejado"), ("VALIDATING", "Validando"), ("READY", "Pronto"), ("RUNNING", "Executando"), ("VERIFYING", "Verificando"), ("SUCCEEDED", "Concluído"), ("FAILED", "Falhou"), ("CANCELLED", "Cancelado")], default="PLANNED", max_length=20)),
                ("executor", models.CharField(max_length=20)),
                ("strategy", models.CharField(max_length=30)),
                ("config_snapshot", models.JSONField(default=dict)),
                ("release_observada", models.CharField(blank=True, max_length=50)),
                ("erro", models.TextField(blank=True)),
                ("etapas", models.JSONField(blank=True, default=list)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("iniciado_em", models.DateTimeField(blank=True, null=True)),
                ("finalizado_em", models.DateTimeField(blank=True, null=True)),
                ("ambiente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="deployment_plans", to="sistema.ambiente")),
                ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="deployment_plans", to=settings.AUTH_USER_MODEL)),
                ("sistema", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deployment_plans", to="sistema.sistema")),
                ("versao", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="deployment_plans", to="sistema.versaogeracao")),
            ],
            options={"verbose_name": "Plano de Deployment", "verbose_name_plural": "Planos de Deployment", "ordering": ["-criado_em", "-id"]},
        ),
    ]
