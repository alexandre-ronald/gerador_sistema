from django.db import migrations, models


def repair_related_name_str(apps, schema_editor):
    """Repair databases where migration 0002 was recorded but the column is absent.

    This is intentionally idempotent and database-agnostic. It fixes the real
    failure mode seen in generated-system/runtime flows without requiring the
    user to delete the database or fake migrations.
    """
    table_name = "sistema_campo"
    column_name = "related_name_str"

    connection = schema_editor.connection
    existing_columns = {
        field.name for field in connection.introspection.get_table_description(
            connection.cursor(), table_name
        )
    }

    if column_name in existing_columns:
        return

    field = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Related Name",
    )
    field.set_attributes_from_name(column_name)
    schema_editor.add_field(
        apps.get_model("sistema", "Campo"),
        field,
    )


def noop(apps, schema_editor):
    # The repair is deliberately not reversed: removing a column would be
    # destructive for a database that already had the field before migration.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("sistema", "0003_sistema_tipo_menu"),
    ]

    operations = [
        migrations.RunPython(repair_related_name_str, noop),
    ]
