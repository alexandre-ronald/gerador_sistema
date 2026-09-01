from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0009_generation_contract"),
    ]

    operations = [
        migrations.AddField(
            model_name="versaogeracao",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Rascunho"),
                    ("VALIDATING", "Em validação"),
                    ("VALIDATED", "Validada"),
                    ("RELEASED", "Publicada"),
                ],
                default="DRAFT",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="versaogeracao",
            name="changelog",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="versaogeracao",
            name="validado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="versaogeracao",
            name="publicado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
