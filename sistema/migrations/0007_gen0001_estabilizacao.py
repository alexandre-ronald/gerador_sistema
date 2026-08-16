from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sistema", "0006_sistema_slug_sistema_usuario")]
    operations = [
        migrations.AlterField(
            model_name="sistema",
            name="usar_custom_user",
            field=models.BooleanField(default=False, verbose_name="Gerar Custom User Model?"),
        ),
        migrations.AlterField(
            model_name="sistema",
            name="banco_dados",
            field=models.CharField(
                choices=[("sqlite3", "SQLite"), ("postgresql", "PostgreSQL")],
                default="sqlite3",
                max_length=50,
                verbose_name="Banco de dados",
            ),
        ),
    ]
