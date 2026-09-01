from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0010_release_manager"),
    ]

    operations = [
        migrations.CreateModel(
            name="Ambiente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("DEVELOPMENT", "Development"), ("TEST", "Test"), ("STAGING", "Staging"), ("PRODUCTION", "Production")], max_length=20)),
                ("nome", models.CharField(max_length=100)),
                ("url_base", models.URLField(blank=True)),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("release_atual", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ambientes_atuais", to="sistema.versaogeracao")),
                ("sistema", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ambientes", to="sistema.sistema")),
            ],
            options={
                "verbose_name": "Ambiente",
                "verbose_name_plural": "Ambientes",
                "ordering": ["sistema", "tipo"],
            },
        ),
        migrations.CreateModel(
            name="PromocaoAmbiente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("promovido_em", models.DateTimeField(auto_now_add=True)),
                ("observacao", models.CharField(blank=True, max_length=255)),
                ("ambiente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="promocoes", to="sistema.ambiente")),
                ("versao", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="promocoes_ambiente", to="sistema.versaogeracao")),
            ],
            options={
                "verbose_name": "Promoção de Ambiente",
                "verbose_name_plural": "Promoções de Ambiente",
                "ordering": ["-promovido_em", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="ambiente",
            constraint=models.UniqueConstraint(fields=("sistema", "tipo"), name="uniq_ambiente_sistema_tipo"),
        ),
    ]
