from django.db import migrations

ROLE_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {"start_agentrun", "view_agentrun", "review_agentrun"},
    "executive_manager": {
        "start_agentrun",
        "view_agentrun",
        "review_agentrun",
        "approve_agentproposal",
        "execute_agentproposal",
    },
    "project_manager": {
        "start_agentrun",
        "view_agentrun",
        "review_agentrun",
        "approve_agentproposal",
        "execute_agentproposal",
    },
    "supervisor": {
        "start_agentrun",
        "view_agentrun",
        "review_agentrun",
        "approve_agentproposal",
        "execute_agentproposal",
    },
    "employee": set(),
    "contractor": set(),
}

PERMISSION_NAMES = {
    "start_agentrun": "Can start project agent runs",
    "view_agentrun": "Can view agent run",
    "review_agentrun": "Can review completed project agent runs",
    "approve_agentproposal": "Can approve project agent proposals",
    "execute_agentproposal": "Can execute approved agent proposals",
}


def seed_phase17_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="project_agents", model="agentrun"
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


def remove_phase17_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(
        content_type__app_label="project_agents",
        codename__in=PERMISSION_NAMES,
    )
    for group in Group.objects.filter(name__in=ROLE_PERMISSIONS):
        group.permissions.remove(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("project_agents", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_phase17_permissions, remove_phase17_permissions),
    ]
