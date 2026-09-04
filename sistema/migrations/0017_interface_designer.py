from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0016_sistema_tipo_sistema"),
    ]

    operations = [
        migrations.AddField(
            model_name="sistema",
            name="interface_modo",
            field=models.CharField(
                choices=[("automatico", "Automático"), ("claro", "Claro"), ("escuro", "Escuro")],
                default="automatico",
                max_length=20,
                verbose_name="Modo da interface",
            ),
        ),
        migrations.AddField(
            model_name="sistema",
            name="interface_densidade",
            field=models.CharField(
                choices=[("compacta", "Compacta"), ("confortavel", "Confortável"), ("espacosa", "Espaçosa")],
                default="confortavel",
                max_length=20,
                verbose_name="Densidade da interface",
            ),
        ),
        migrations.AddField(
            model_name="sistema",
            name="interface_nome",
            field=models.CharField(blank=True, max_length=100, verbose_name="Nome exibido na interface"),
        ),
        migrations.AddField(
            model_name="sistema",
            name="interface_cor_primaria",
            field=models.CharField(default="#0d6efd", max_length=7, verbose_name="Cor principal"),
        ),
        migrations.AddField(
            model_name="sistema",
            name="interface_cor_destaque",
            field=models.CharField(default="#6f42c1", max_length=7, verbose_name="Cor de destaque"),
        ),
        migrations.AddField(
            model_name="sistema",
            name="interface_breadcrumb",
            field=models.BooleanField(default=True, verbose_name="Exibir breadcrumb"),
        ),
        migrations.AddField(
            model_name="sistema",
            name="interface_busca",
            field=models.BooleanField(default=True, verbose_name="Exibir busca"),
        ),
        migrations.AddField(
            model_name="sistema",
            name="interface_menu_usuario",
            field=models.BooleanField(default=True, verbose_name="Exibir menu do usuário"),
        ),
    ]
