from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0012_runtime_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="runtimesnapshot",
            name="latency_ms",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="RuntimeCheck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("online", models.BooleanField(default=False)),
                ("health", models.CharField(default="UNKNOWN", max_length=20)),
                ("release_observada", models.CharField(blank=True, max_length=50)),
                ("migrations_pending", models.PositiveIntegerField(default=0)),
                ("latency_ms", models.PositiveIntegerField(default=0)),
                ("erro", models.TextField(blank=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("verificado_em", models.DateTimeField(auto_now_add=True)),
                ("ambiente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runtime_checks", to="sistema.ambiente")),
            ],
            options={
                "verbose_name": "Verificação de Runtime",
                "verbose_name_plural": "Verificações de Runtime",
                "ordering": ["-verificado_em", "-id"],
            },
        ),
    ]
