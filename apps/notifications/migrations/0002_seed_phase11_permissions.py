from django.db import migrations


def seed_phase11_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="notifications",
        model="deliveryattempt",
    )
    permission, _created = Permission.objects.get_or_create(
        content_type=content_type,
        codename="view_delivery_status",
        defaults={"name": "Can view notification delivery status"},
    )
    group, _created = Group.objects.get_or_create(name="technical_admin")
    group.permissions.add(permission)


def remove_phase11_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permission = Permission.objects.filter(
        content_type__app_label="notifications",
        content_type__model="deliveryattempt",
        codename="view_delivery_status",
    ).first()
    group = Group.objects.filter(name="technical_admin").first()
    if permission is not None and group is not None:
        group.permissions.remove(permission)
    if permission is not None:
        permission.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            seed_phase11_permissions,
            remove_phase11_permissions,
        ),
    ]
