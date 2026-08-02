from django.db import migrations

ROLE_PERMISSIONS = {
    "technical_admin": {
        "view_operations_status",
        "view_archive_center",
    },
    "ceo": set(),
    "executive_manager": {"view_archive_center"},
    "project_manager": {"view_archive_center"},
    "supervisor": set(),
    "employee": set(),
    "contractor": set(),
}

PERMISSION_NAMES = {
    "view_operations_status": "Can view safe operations status",
    "view_archive_center": "Can view the archive center",
}


def seed_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="operations",
        model="operationsaccess",
    )
    permissions = {}
    for codename, name in PERMISSION_NAMES.items():
        permission, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions[codename] = permission
    for role, codenames in ROLE_PERMISSIONS.items():
        group, _created = Group.objects.get_or_create(name=role)
        group.permissions.add(
            *[permissions[codename] for codename in sorted(codenames)]
        )


def remove_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(
        content_type__app_label="operations",
        content_type__model="operationsaccess",
        codename__in=PERMISSION_NAMES,
    )
    for group in Group.objects.filter(name__in=ROLE_PERMISSIONS):
        group.permissions.remove(*permissions)
    permissions.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("operations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, remove_permissions),
    ]
