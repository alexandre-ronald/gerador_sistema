from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0015_observabilityevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="sistema",
            name="tipo_sistema",
            field=models.CharField(
                choices=[
                    ("cadastro", "Cadastro e Controle"),
                    ("workflow", "Solicitações e Workflow"),
                    ("gestao", "Gestão e Acompanhamento"),
                    ("vazio", "Começar vazio"),
                ],
                default="vazio",
                max_length=20,
                verbose_name="Tipo inicial",
            ),
        ),
    ]
