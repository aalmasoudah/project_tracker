from django.db import migrations

ROLE_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {
        ("attendanceentry", "view_attendanceentry"),
        ("attendancesubmission", "view_attendancesubmission"),
        ("session", "manage_all_sessions"),
        ("session", "view_session"),
        ("sessionparticipant", "view_sessionparticipant"),
    },
    "executive_manager": {
        ("attendanceentry", "view_attendanceentry"),
        ("attendanceevidence", "view_attendanceevidence"),
        ("attendancesubmission", "view_attendancesubmission"),
        ("session", "add_session"),
        ("session", "archive_session"),
        ("session", "change_session"),
        ("session", "issue_trainer_link"),
        ("session", "manage_all_sessions"),
        ("session", "view_session"),
        ("sessionparticipant", "view_sessionparticipant"),
        ("trainerlink", "view_trainerlink"),
    },
    "project_manager": {
        ("attendanceentry", "view_attendanceentry"),
        ("attendanceevidence", "view_attendanceevidence"),
        ("attendancesubmission", "view_attendancesubmission"),
        ("session", "add_session"),
        ("session", "archive_session"),
        ("session", "change_session"),
        ("session", "issue_trainer_link"),
        ("session", "manage_managed_sessions"),
        ("session", "view_session"),
        ("sessionparticipant", "view_sessionparticipant"),
        ("trainerlink", "view_trainerlink"),
    },
    "supervisor": {
        ("attendanceentry", "view_attendanceentry"),
        ("attendancesubmission", "view_attendancesubmission"),
        ("session", "view_context_sessions"),
        ("session", "view_session"),
        ("sessionparticipant", "view_sessionparticipant"),
    },
    "employee": set(),
    "contractor": set(),
}


CUSTOM_NAMES = {
    ("session", "archive_session"): "Can archive sessions",
    ("session", "issue_trainer_link"): "Can issue trainer links",
    ("session", "manage_all_sessions"): "Can manage all sessions",
    ("session", "manage_managed_sessions"): "Can manage sessions in managed courses",
    ("session", "view_context_sessions"): "Can view active context sessions",
}


def seed_phase9_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = {}
    keys = set().union(*ROLE_PERMISSIONS.values())
    for key in sorted(keys):
        model, codename = key
        content_type, _created = ContentType.objects.get_or_create(
            app_label="attendance", model=model
        )
        name = CUSTOM_NAMES.get(key, f"Can {codename.replace('_', ' ')}")
        permission, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions[key] = permission
    for role, role_keys in ROLE_PERMISSIONS.items():
        group, _created = Group.objects.get_or_create(name=role)
        group.permissions.add(*[permissions[key] for key in sorted(role_keys)])


def remove_phase9_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(content_type__app_label="attendance")
    for group in Group.objects.filter(name__in=ROLE_PERMISSIONS):
        group.permissions.remove(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("attendance", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_phase9_permissions, remove_phase9_permissions)
    ]
