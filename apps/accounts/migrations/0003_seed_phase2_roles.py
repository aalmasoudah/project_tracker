from django.db import migrations

ROLE_PERMISSIONS = {
    "technical_admin": {
        ("accounts", "add_user"),
        ("accounts", "change_user"),
        ("accounts", "manage_accounts"),
        ("accounts", "view_all_directory"),
        ("accounts", "view_user"),
        ("audit", "view_auditevent"),
        ("organizations", "add_department"),
        ("organizations", "archive_department"),
        ("organizations", "change_department"),
        ("organizations", "restore_department"),
        ("organizations", "view_all_departments"),
        ("organizations", "view_department"),
    },
    "ceo": {
        ("accounts", "view_all_directory"),
        ("accounts", "view_user"),
        ("organizations", "view_all_departments"),
        ("organizations", "view_department"),
    },
    "executive_manager": {
        ("accounts", "view_all_directory"),
        ("accounts", "view_user"),
        ("organizations", "view_all_departments"),
        ("organizations", "view_department"),
    },
    "project_manager": {
        ("accounts", "view_department_directory"),
        ("accounts", "view_user"),
        ("organizations", "view_department"),
    },
    "supervisor": {
        ("accounts", "view_department_directory"),
        ("accounts", "view_user"),
        ("organizations", "view_department"),
    },
    "employee": {
        ("accounts", "view_own_profile"),
        ("accounts", "view_user"),
        ("organizations", "view_department"),
    },
    "contractor": {
        ("accounts", "view_own_profile"),
        ("accounts", "view_user"),
        ("organizations", "view_department"),
    },
}

PERMISSION_NAMES = {
    ("accounts", "add_user"): "Can add user",
    ("accounts", "change_user"): "Can change user",
    ("accounts", "manage_accounts"): "Can administer internal accounts",
    ("accounts", "view_all_directory"): "Can view the complete active directory",
    (
        "accounts",
        "view_department_directory",
    ): "Can view the active directory for own department",
    ("accounts", "view_own_profile"): "Can view own account profile",
    ("accounts", "view_user"): "Can view user",
    ("audit", "view_auditevent"): "Can view audit event",
    ("organizations", "add_department"): "Can add department",
    (
        "organizations",
        "archive_department",
    ): "Can archive departments",
    ("organizations", "change_department"): "Can change department",
    (
        "organizations",
        "restore_department",
    ): "Can restore departments",
    (
        "organizations",
        "view_all_departments",
    ): "Can view all active departments",
    ("organizations", "view_department"): "Can view department",
}

MODEL_NAMES = {
    "accounts": "user",
    "audit": "auditevent",
    "organizations": "department",
}


def seed_roles(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    permissions = {}
    for key, permission_name in PERMISSION_NAMES.items():
        app_label, codename = key
        content_type, _created = ContentType.objects.get_or_create(
            app_label=app_label,
            model=MODEL_NAMES[app_label],
        )
        permission, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": permission_name},
        )
        permissions[key] = permission

    for role_code, permission_keys in ROLE_PERMISSIONS.items():
        group, _created = Group.objects.get_or_create(name=role_code)
        group.permissions.set([permissions[key] for key in sorted(permission_keys)])


def remove_roles(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLE_PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_phase2_account_identity"),
        ("audit", "0001_initial"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, remove_roles),
    ]
