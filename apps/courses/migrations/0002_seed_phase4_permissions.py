from django.db import migrations

ROLE_COURSE_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {
        ("course", "view_all_courses"),
        ("course", "view_course"),
        ("course", "view_course_history"),
        ("coursefile", "view_coursefile"),
        ("trainer", "view_trainer"),
        ("trainer", "view_trainer_contact"),
    },
    "executive_manager": {
        ("course", "add_course"),
        ("course", "archive_course"),
        ("course", "change_course"),
        ("course", "manage_course_trainers"),
        ("course", "restore_course"),
        ("course", "upload_course_file"),
        ("course", "view_all_courses"),
        ("course", "view_course"),
        ("course", "view_course_history"),
        ("coursefile", "view_coursefile"),
        ("trainer", "add_trainer"),
        ("trainer", "archive_trainer"),
        ("trainer", "change_trainer"),
        ("trainer", "restore_trainer"),
        ("trainer", "view_trainer"),
        ("trainer", "view_trainer_contact"),
    },
    "project_manager": {
        ("course", "add_course"),
        ("course", "archive_course"),
        ("course", "change_course"),
        ("course", "manage_course_trainers"),
        ("course", "restore_course"),
        ("course", "upload_course_file"),
        ("course", "view_course"),
        ("course", "view_course_history"),
        ("course", "view_managed_courses"),
        ("coursefile", "view_coursefile"),
        ("trainer", "view_trainer"),
        ("trainer", "view_trainer_contact"),
    },
    "supervisor": {
        ("course", "view_assigned_courses"),
        ("course", "view_course"),
        ("coursefile", "view_coursefile"),
    },
    "employee": {
        ("course", "view_assigned_courses"),
        ("course", "view_course"),
        ("coursefile", "view_coursefile"),
    },
    "contractor": {
        ("course", "view_assigned_courses"),
        ("course", "view_course"),
        ("coursefile", "view_coursefile"),
    },
}

PERMISSION_NAMES = {
    ("course", "add_course"): "Can add course",
    ("course", "archive_course"): "Can archive courses",
    ("course", "change_course"): "Can change course",
    ("course", "manage_course_trainers"): "Can manage course trainers",
    ("course", "restore_course"): "Can restore courses",
    ("course", "upload_course_file"): "Can upload course files",
    ("course", "view_all_courses"): "Can view all courses",
    ("course", "view_assigned_courses"): "Can view assigned courses",
    ("course", "view_course"): "Can view course",
    ("course", "view_course_history"): "Can view course history",
    ("course", "view_managed_courses"): "Can view managed courses",
    ("coursefile", "view_coursefile"): "Can view course file",
    ("trainer", "add_trainer"): "Can add trainer",
    ("trainer", "archive_trainer"): "Can archive trainers",
    ("trainer", "change_trainer"): "Can change trainer",
    ("trainer", "restore_trainer"): "Can restore trainers",
    ("trainer", "view_trainer"): "Can view trainer",
    ("trainer", "view_trainer_contact"): "Can view trainer contact data",
}


def add_phase4_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = {}
    for key, permission_name in PERMISSION_NAMES.items():
        model_name, codename = key
        content_type, _created = ContentType.objects.get_or_create(
            app_label="courses",
            model=model_name,
        )
        permission, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": permission_name},
        )
        permissions[key] = permission
    for role_code, permission_keys in ROLE_COURSE_PERMISSIONS.items():
        group, _created = Group.objects.get_or_create(name=role_code)
        group.permissions.add(*[permissions[key] for key in sorted(permission_keys)])


def remove_phase4_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    course_permissions = Permission.objects.filter(
        content_type__app_label="courses",
    )
    for group in Group.objects.filter(name__in=ROLE_COURSE_PERMISSIONS):
        group.permissions.remove(*course_permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_phase4_permissions, remove_phase4_permissions),
    ]
