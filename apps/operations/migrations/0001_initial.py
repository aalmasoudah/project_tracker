# Generated for the approved Phase 14 operations permissions.

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OperationsAccess",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
            options={
                "permissions": (
                    (
                        "view_operations_status",
                        "Can view safe operations status",
                    ),
                    ("view_archive_center", "Can view the archive center"),
                ),
                "managed": False,
                "default_permissions": (),
            },
        ),
    ]
