from django.db import migrations

ROLE_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {
        "receive_critical_alert",
        "request_executivereport",
        "view_executivereportrequest",
    },
    "executive_manager": set(),
    "project_manager": set(),
    "supervisor": set(),
    "employee": set(),
    "contractor": set(),
}

PERMISSION_NAMES = {
    "receive_critical_alert": "Can receive CEO critical task alerts",
    "request_executivereport": "Can request CEO Telegram reports",
    "view_executivereportrequest": "Can view executive report request",
}


def seed_phase16_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="executive_bot",
        model="executivereportrequest",
    )
    permissions = {}
    for codename, name in PERMISSION_NAMES.items():
        permission, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions[codename] = permission
    for role_code, codenames in ROLE_PERMISSIONS.items():
        group, _created = Group.objects.get_or_create(name=role_code)
        group.permissions.add(
            *[permissions[codename] for codename in sorted(codenames)]
        )


def remove_phase16_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(
        content_type__app_label="executive_bot",
        codename__in=PERMISSION_NAMES,
    )
    for group in Group.objects.filter(name__in=ROLE_PERMISSIONS):
        group.permissions.remove(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("executive_bot", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_phase16_permissions, remove_phase16_permissions),
    ]
