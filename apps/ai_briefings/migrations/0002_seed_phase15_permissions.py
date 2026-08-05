from django.db import migrations

ROLE_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {
        "generate_aibriefing",
        "review_aibriefing",
        "view_aibriefing",
    },
    "executive_manager": {
        "generate_aibriefing",
        "review_aibriefing",
        "view_aibriefing",
    },
    "project_manager": {
        "generate_aibriefing",
        "review_aibriefing",
        "view_aibriefing",
    },
    "supervisor": {
        "generate_aibriefing",
        "review_aibriefing",
        "view_aibriefing",
    },
    "employee": set(),
    "contractor": set(),
}

PERMISSION_NAMES = {
    "generate_aibriefing": "Can generate AI project briefings",
    "review_aibriefing": "Can review AI project briefings",
    "view_aibriefing": "Can view AI briefing",
}


def seed_phase15_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="ai_briefings",
        model="aibriefing",
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


def remove_phase15_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(
        content_type__app_label="ai_briefings",
        codename__in=PERMISSION_NAMES,
    )
    for group in Group.objects.filter(name__in=ROLE_PERMISSIONS):
        group.permissions.remove(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("ai_briefings", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            seed_phase15_permissions,
            remove_phase15_permissions,
        ),
    ]
