from django.db import migrations

ROLE_APPROVAL_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {
        ("approvalrequest", "view_all_approvals"),
        ("approvalrequest", "view_approvalrequest"),
        ("milestone", "view_all_milestones"),
        ("milestone", "view_milestone"),
    },
    "executive_manager": {
        ("approvalrequest", "submit_approval"),
        ("approvalrequest", "view_all_approvals"),
        ("approvalrequest", "view_approvalrequest"),
        ("milestone", "add_milestone"),
        ("milestone", "archive_milestone"),
        ("milestone", "change_milestone"),
        ("milestone", "restore_milestone"),
        ("milestone", "view_all_milestones"),
        ("milestone", "view_milestone"),
    },
    "project_manager": {
        ("approvalrequest", "decide_manager_approval"),
        ("approvalrequest", "submit_approval"),
        ("approvalrequest", "view_approvalrequest"),
        ("approvalrequest", "view_managed_approvals"),
        ("milestone", "add_milestone"),
        ("milestone", "archive_milestone"),
        ("milestone", "change_milestone"),
        ("milestone", "restore_milestone"),
        ("milestone", "view_managed_milestones"),
        ("milestone", "view_milestone"),
    },
    "supervisor": {
        ("approvalrequest", "decide_supervisor_approval"),
        ("approvalrequest", "submit_approval"),
        ("approvalrequest", "view_approvalrequest"),
        ("approvalrequest", "view_context_approvals"),
        ("milestone", "view_context_milestones"),
        ("milestone", "view_milestone"),
    },
    "employee": {
        ("approvalrequest", "submit_approval"),
        ("approvalrequest", "view_approvalrequest"),
        ("approvalrequest", "view_own_approvals"),
        ("milestone", "view_context_milestones"),
        ("milestone", "view_milestone"),
    },
    "contractor": {
        ("approvalrequest", "submit_approval"),
        ("approvalrequest", "view_approvalrequest"),
        ("approvalrequest", "view_own_approvals"),
        ("milestone", "view_context_milestones"),
        ("milestone", "view_milestone"),
    },
}

PERMISSION_NAMES = {
    ("approvalrequest", "decide_manager_approval"): (
        "Can decide Project Manager approval"
    ),
    ("approvalrequest", "decide_supervisor_approval"): (
        "Can decide Supervisor approval"
    ),
    ("approvalrequest", "submit_approval"): "Can submit completion approval",
    ("approvalrequest", "view_all_approvals"): "Can view all approvals",
    ("approvalrequest", "view_approvalrequest"): "Can view approval request",
    ("approvalrequest", "view_context_approvals"): "Can view context approvals",
    ("approvalrequest", "view_managed_approvals"): "Can view managed approvals",
    ("approvalrequest", "view_own_approvals"): "Can view own approvals",
    ("milestone", "add_milestone"): "Can add milestone",
    ("milestone", "archive_milestone"): "Can archive milestones",
    ("milestone", "change_milestone"): "Can change milestone",
    ("milestone", "restore_milestone"): "Can restore milestones",
    ("milestone", "view_all_milestones"): "Can view all milestones",
    ("milestone", "view_context_milestones"): "Can view context milestones",
    ("milestone", "view_managed_milestones"): "Can view managed milestones",
    ("milestone", "view_milestone"): "Can view milestone",
}


def add_phase7_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = {}
    for key, permission_name in PERMISSION_NAMES.items():
        model_name, codename = key
        content_type, _created = ContentType.objects.get_or_create(
            app_label="approvals",
            model=model_name,
        )
        permission, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": permission_name},
        )
        permissions[key] = permission
    for role_code, permission_keys in ROLE_APPROVAL_PERMISSIONS.items():
        group, _created = Group.objects.get_or_create(name=role_code)
        group.permissions.add(*[permissions[key] for key in sorted(permission_keys)])


def remove_phase7_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    approval_permissions = Permission.objects.filter(
        content_type__app_label="approvals"
    )
    for group in Group.objects.filter(name__in=ROLE_APPROVAL_PERMISSIONS):
        group.permissions.remove(*approval_permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("approvals", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_phase7_permissions, remove_phase7_permissions),
    ]
