from django.db import migrations


def normalize_text_field_lengths(apps, schema_editor):
    Campo = apps.get_model("sistema", "Campo")
    Campo.objects.filter(
        tipo__in=["CharField", "EmailField", "URLField"],
        max_length__isnull=True,
    ).update(max_length=255)


class Migration(migrations.Migration):
    dependencies = [
        ("sistema", "0008_alter_campo_default_value"),
    ]

    operations = [
        migrations.RunPython(
            normalize_text_field_lengths,
            migrations.RunPython.noop,
        ),
    ]
