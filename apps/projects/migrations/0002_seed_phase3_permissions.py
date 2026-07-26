from django.db import migrations

ROLE_PROJECT_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {
        ("category", "view_category"),
        ("client", "view_client"),
        ("project", "view_all_projects"),
        ("project", "view_project"),
        ("project", "view_project_budget"),
        ("project", "view_project_history"),
    },
    "executive_manager": {
        ("category", "add_category"),
        ("category", "archive_category"),
        ("category", "change_category"),
        ("category", "restore_category"),
        ("category", "view_category"),
        ("client", "add_client"),
        ("client", "archive_client"),
        ("client", "change_client"),
        ("client", "restore_client"),
        ("client", "view_client"),
        ("project", "add_project"),
        ("project", "archive_project"),
        ("project", "change_project"),
        ("project", "manage_project_team"),
        ("project", "restore_project"),
        ("project", "view_all_projects"),
        ("project", "view_project"),
        ("project", "view_project_budget"),
        ("project", "view_project_history"),
    },
    "project_manager": {
        ("category", "view_category"),
        ("client", "view_client"),
        ("project", "add_project"),
        ("project", "archive_project"),
        ("project", "change_project"),
        ("project", "manage_project_team"),
        ("project", "restore_project"),
        ("project", "view_managed_projects"),
        ("project", "view_project"),
        ("project", "view_project_budget"),
        ("project", "view_project_history"),
    },
    "supervisor": {
        ("project", "view_assigned_projects"),
        ("project", "view_project"),
    },
    "employee": {
        ("project", "view_assigned_projects"),
        ("project", "view_project"),
    },
    "contractor": {
        ("project", "view_assigned_projects"),
        ("project", "view_project"),
    },
}

PERMISSION_NAMES = {
    ("category", "add_category"): "Can add category",
    ("category", "archive_category"): "Can archive categories",
    ("category", "change_category"): "Can change category",
    ("category", "restore_category"): "Can restore categories",
    ("category", "view_category"): "Can view category",
    ("client", "add_client"): "Can add client",
    ("client", "archive_client"): "Can archive clients",
    ("client", "change_client"): "Can change client",
    ("client", "restore_client"): "Can restore clients",
    ("client", "view_client"): "Can view client",
    ("project", "add_project"): "Can add project",
    ("project", "archive_project"): "Can archive projects",
    ("project", "change_project"): "Can change project",
    ("project", "manage_project_team"): "Can manage project teams",
    ("project", "restore_project"): "Can restore projects",
    ("project", "view_all_projects"): "Can view all projects",
    ("project", "view_assigned_projects"): "Can view assigned projects",
    ("project", "view_managed_projects"): "Can view managed projects",
    ("project", "view_project"): "Can view project",
    ("project", "view_project_budget"): "Can view project budgets",
    ("project", "view_project_history"): "Can view project history",
}


def add_phase3_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    permissions = {}
    for key, permission_name in PERMISSION_NAMES.items():
        model_name, codename = key
        content_type, _created = ContentType.objects.get_or_create(
            app_label="projects",
            model=model_name,
        )
        permission, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": permission_name},
        )
        permissions[key] = permission

    for role_code, permission_keys in ROLE_PROJECT_PERMISSIONS.items():
        group, _created = Group.objects.get_or_create(name=role_code)
        group.permissions.add(*[permissions[key] for key in sorted(permission_keys)])


def remove_phase3_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    project_permissions = Permission.objects.filter(
        content_type__app_label="projects",
    )
    for group in Group.objects.filter(name__in=ROLE_PROJECT_PERMISSIONS):
        group.permissions.remove(*project_permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("audit", "0002_auditevent_scope"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            add_phase3_permissions,
            remove_phase3_permissions,
        ),
    ]
