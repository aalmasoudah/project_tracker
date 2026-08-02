from django.db import migrations

ROLE_PERMISSIONS = {
    "technical_admin": {
        "view_security_audit",
        "export_security_audit",
    },
    "ceo": {
        "view_business_audit",
        "export_business_audit",
    },
    "executive_manager": {
        "view_business_audit",
        "export_business_audit",
    },
    "project_manager": set(),
    "supervisor": set(),
    "employee": set(),
    "contractor": set(),
}

PERMISSION_NAMES = {
    "view_security_audit": "Can view security and operations audit",
    "view_business_audit": "Can view business audit",
    "export_security_audit": "Can export security and operations audit",
    "export_business_audit": "Can export business audit",
}


def seed_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="audit",
        model="auditevent",
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
        content_type__app_label="audit",
        content_type__model="auditevent",
        codename__in=PERMISSION_NAMES,
    )
    for group in Group.objects.filter(name__in=ROLE_PERMISSIONS):
        group.permissions.remove(*permissions)
    permissions.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("audit", "0009_phase14_audit_permissions_indexes"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, remove_permissions),
    ]
