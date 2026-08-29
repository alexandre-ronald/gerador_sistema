from django.db import migrations, models


def enable_crud_for_existing_entities(apps, schema_editor):
    Entidade = apps.get_model("sistema", "Entidade")
    Entidade.objects.filter(gerar_crud_views=False).update(gerar_crud_views=True)


class Migration(migrations.Migration):
    dependencies = [("sistema", "0008_versao_geracao")]

    operations = [
        migrations.AlterField(
            model_name="entidade",
            name="gerar_crud_views",
            field=models.BooleanField(default=True, verbose_name="Gerar Views e Templates de CRUD?"),
        ),
        migrations.RunPython(enable_crud_for_existing_entities, migrations.RunPython.noop),
    ]
