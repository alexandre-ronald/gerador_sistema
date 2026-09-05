from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0017_interface_designer"),
    ]

    operations = [
        migrations.AddField(
            model_name="sistema",
            name="interface_notificacoes",
            field=models.BooleanField(
                default=True,
                verbose_name="Exibir notificações no cabeçalho",
            ),
        ),
    ]
