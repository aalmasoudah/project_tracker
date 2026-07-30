from django.db import migrations

ALL_EXPORTS = {
    "export_project_progress",
    "export_overdue_tasks",
    "export_course_attendance",
    "export_project_attendance",
}

ROLE_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": ALL_EXPORTS,
    "executive_manager": ALL_EXPORTS,
    "project_manager": ALL_EXPORTS,
    "supervisor": {
        "export_course_attendance",
        "export_project_attendance",
    },
    "employee": set(),
    "contractor": set(),
}

PERMISSION_NAMES = {
    "export_project_progress": "Can export project progress reports",
    "export_overdue_tasks": "Can export overdue task reports",
    "export_course_attendance": "Can export course attendance reports",
    "export_project_attendance": "Can export project attendance reports",
}


def seed_phase13_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="reports",
        model="reportaccess",
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


def remove_phase13_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(
        content_type__app_label="reports",
        content_type__model="reportaccess",
        codename__in=PERMISSION_NAMES,
    )
    for group in Group.objects.filter(name__in=ROLE_PERMISSIONS):
        group.permissions.remove(*permissions)
    permissions.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            seed_phase13_permissions,
            remove_phase13_permissions,
        )
    ]
