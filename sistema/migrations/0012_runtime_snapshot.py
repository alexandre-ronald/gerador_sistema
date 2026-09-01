from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0011_environment_manager"),
    ]

    operations = [
        migrations.CreateModel(
            name="RuntimeSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("online", models.BooleanField(default=False)),
                ("contract", models.CharField(blank=True, max_length=20)),
                ("status", models.CharField(blank=True, max_length=30)),
                ("release_observada", models.CharField(blank=True, max_length=50)),
                ("ambiente_observado", models.CharField(blank=True, max_length=50)),
                ("database_vendor", models.CharField(blank=True, max_length=50)),
                ("migrations_pending", models.PositiveIntegerField(default=0)),
                ("uptime_seconds", models.PositiveBigIntegerField(default=0)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("erro", models.TextField(blank=True)),
                ("verificado_em", models.DateTimeField(auto_now=True)),
                ("ambiente", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="runtime_snapshot", to="sistema.ambiente")),
            ],
            options={
                "verbose_name": "Snapshot de Runtime",
                "verbose_name_plural": "Snapshots de Runtime",
            },
        ),
    ]
