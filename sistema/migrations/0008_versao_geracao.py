from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sistema", "0007_repair_campo_related_name_str"),
    ]

    operations = [
        migrations.CreateModel(
            name="VersaoGeracao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.PositiveIntegerField()),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("descricao", models.CharField(blank=True, max_length=255)),
                ("estrutura_json", models.JSONField(default=dict)),
                ("arquivo_zip", models.FileField(blank=True, null=True, upload_to="sistemas_versoes/")),
                ("sistema", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versoes", to="sistema.sistema")),
            ],
            options={
                "verbose_name": "Versão de Geração",
                "verbose_name_plural": "Versões de Geração",
                "ordering": ["-numero"],
            },
        ),
        migrations.AddConstraint(
            model_name="versaogeracao",
            constraint=models.UniqueConstraint(fields=("sistema", "numero"), name="uniq_versao_sistema_numero"),
        ),
    ]
