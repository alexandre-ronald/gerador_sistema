from django.db import migrations, models


def repair_related_name_str(apps, schema_editor):
    """Repair databases where 0002 recorded the field but the column is absent.

    Migration 0002 already defines ``Campo.related_name_str``. This migration
    only repairs databases whose migration history says 0002 was applied while
    the physical column is missing. It is intentionally idempotent and does
    not alter databases where the column is already present.
    """
    table_name = "sistema_campo"
    column_name = "related_name_str"

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existing_columns = {
            field.name
            for field in connection.introspection.get_table_description(
                cursor, table_name
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
    # Do not remove the column on reverse. The migration repairs an existing
    # database and deleting the repaired column would be destructive.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("sistema", "0006_sistema_slug_sistema_usuario"),
    ]

    operations = [
        migrations.RunPython(repair_related_name_str, noop),
    ]
