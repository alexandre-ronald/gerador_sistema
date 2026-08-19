from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("sistema", "0009_gen0002_normalize_field_defaults"),
    ]

    operations = [
        migrations.RenameField(
            model_name="campo",
            old_name="related_name_str",
            new_name="related_name",
        ),
    ]
