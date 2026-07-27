from django.db import migrations

ROLE_TASK_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {
        ("tag", "view_tag"),
        ("task", "view_all_tasks"),
        ("task", "view_task"),
        ("task", "view_task_history"),
        ("taskfile", "view_taskfile"),
    },
    "executive_manager": {
        ("tag", "add_tag"),
        ("tag", "archive_tag"),
        ("tag", "change_tag"),
        ("tag", "restore_tag"),
        ("tag", "view_tag"),
        ("task", "add_task"),
        ("task", "archive_task"),
        ("task", "change_task"),
        ("task", "comment_task"),
        ("task", "manage_task_assignments"),
        ("task", "restore_task"),
        ("task", "upload_task_file"),
        ("task", "view_all_tasks"),
        ("task", "view_task"),
        ("task", "view_task_history"),
        ("taskfile", "view_taskfile"),
    },
    "project_manager": {
        ("tag", "add_tag"),
        ("tag", "archive_tag"),
        ("tag", "change_tag"),
        ("tag", "restore_tag"),
        ("tag", "view_tag"),
        ("task", "add_task"),
        ("task", "archive_task"),
        ("task", "change_task"),
        ("task", "comment_task"),
        ("task", "manage_task_assignments"),
        ("task", "restore_task"),
        ("task", "upload_task_file"),
        ("task", "view_managed_tasks"),
        ("task", "view_task"),
        ("task", "view_task_history"),
        ("taskfile", "view_taskfile"),
    },
    "supervisor": {
        ("tag", "view_tag"),
        ("task", "comment_task"),
        ("task", "update_assigned_task"),
        ("task", "upload_task_file"),
        ("task", "view_context_tasks"),
        ("task", "view_task"),
        ("taskfile", "view_taskfile"),
    },
    "employee": {
        ("tag", "view_tag"),
        ("task", "comment_task"),
        ("task", "update_assigned_task"),
        ("task", "upload_task_file"),
        ("task", "view_assigned_tasks"),
        ("task", "view_task"),
        ("taskfile", "view_taskfile"),
    },
    "contractor": {
        ("tag", "view_tag"),
        ("task", "comment_task"),
        ("task", "update_assigned_task"),
        ("task", "upload_task_file"),
        ("task", "view_assigned_tasks"),
        ("task", "view_task"),
        ("taskfile", "view_taskfile"),
    },
}


PERMISSION_NAMES = {
    ("tag", "add_tag"): "Can add tag",
    ("tag", "archive_tag"): "Can archive task tags",
    ("tag", "change_tag"): "Can change tag",
    ("tag", "restore_tag"): "Can restore task tags",
    ("tag", "view_tag"): "Can view tag",
    ("task", "add_task"): "Can add task",
    ("task", "archive_task"): "Can archive tasks",
    ("task", "change_task"): "Can change task",
    ("task", "comment_task"): "Can comment on tasks",
    ("task", "manage_task_assignments"): "Can manage task assignments",
    ("task", "restore_task"): "Can restore tasks",
    ("task", "update_assigned_task"): "Can update assigned tasks",
    ("task", "upload_task_file"): "Can upload task files",
    ("task", "view_all_tasks"): "Can view all tasks",
    ("task", "view_assigned_tasks"): "Can view assigned tasks",
    ("task", "view_context_tasks"): "Can view context tasks",
    ("task", "view_managed_tasks"): "Can view managed tasks",
    ("task", "view_task"): "Can view task",
    ("task", "view_task_history"): "Can view task history",
    ("taskfile", "view_taskfile"): "Can view task file",
}


def add_phase5_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = {}
    for key, permission_name in PERMISSION_NAMES.items():
        model_name, codename = key
        content_type, _created = ContentType.objects.get_or_create(
            app_label="tasks",
            model=model_name,
        )
        permission, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": permission_name},
        )
        permissions[key] = permission
    for role_code, permission_keys in ROLE_TASK_PERMISSIONS.items():
        group, _created = Group.objects.get_or_create(name=role_code)
        group.permissions.add(*[permissions[key] for key in sorted(permission_keys)])


def remove_phase5_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    task_permissions = Permission.objects.filter(content_type__app_label="tasks")
    for group in Group.objects.filter(name__in=ROLE_TASK_PERMISSIONS):
        group.permissions.remove(*task_permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_phase5_permissions, remove_phase5_permissions),
    ]
