from django.db import migrations

ROLE_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {
        ("courseenrollment", "view_all_enrollments"),
        ("courseenrollment", "view_courseenrollment"),
        ("trainee", "view_trainee"),
    },
    "executive_manager": {
        ("courseenrollment", "add_courseenrollment"),
        ("courseenrollment", "archive_enrollment"),
        ("courseenrollment", "change_courseenrollment"),
        ("courseenrollment", "restore_enrollment"),
        ("courseenrollment", "view_all_enrollments"),
        ("courseenrollment", "view_courseenrollment"),
        ("importbatch", "confirm_trainee_import"),
        ("importbatch", "import_trainees"),
        ("importbatch", "view_import_history"),
        ("importbatch", "view_importbatch"),
        ("importrow", "view_importrow"),
        ("trainee", "add_trainee"),
        ("trainee", "change_trainee"),
        ("trainee", "view_trainee"),
        ("trainee", "view_trainee_contact"),
    },
    "project_manager": {
        ("courseenrollment", "add_courseenrollment"),
        ("courseenrollment", "archive_enrollment"),
        ("courseenrollment", "change_courseenrollment"),
        ("courseenrollment", "restore_enrollment"),
        ("courseenrollment", "view_courseenrollment"),
        ("courseenrollment", "view_managed_enrollments"),
        ("importbatch", "confirm_trainee_import"),
        ("importbatch", "import_trainees"),
        ("importbatch", "view_import_history"),
        ("importbatch", "view_importbatch"),
        ("importrow", "view_importrow"),
        ("trainee", "add_trainee"),
        ("trainee", "change_trainee"),
        ("trainee", "view_trainee"),
        ("trainee", "view_trainee_contact"),
    },
    "supervisor": {
        ("courseenrollment", "view_courseenrollment"),
        ("courseenrollment", "view_roster_enrollments"),
        ("trainee", "view_trainee"),
    },
    "employee": set(),
    "contractor": set(),
}


PERMISSION_NAMES = {
    ("courseenrollment", "add_courseenrollment"): "Can add course enrollment",
    ("courseenrollment", "archive_enrollment"): "Can archive trainee enrollments",
    ("courseenrollment", "change_courseenrollment"): "Can change course enrollment",
    ("courseenrollment", "restore_enrollment"): "Can restore trainee enrollments",
    ("courseenrollment", "view_all_enrollments"): "Can view all trainee enrollments",
    ("courseenrollment", "view_courseenrollment"): "Can view course enrollment",
    (
        "courseenrollment",
        "view_managed_enrollments",
    ): "Can view managed trainee enrollments",
    ("courseenrollment", "view_roster_enrollments"): "Can view limited course rosters",
    ("importbatch", "confirm_trainee_import"): "Can confirm trainee imports",
    ("importbatch", "import_trainees"): "Can preview trainee imports",
    ("importbatch", "view_import_history"): "Can view trainee import history",
    ("importbatch", "view_importbatch"): "Can view import batch",
    ("importrow", "view_importrow"): "Can view import row",
    ("trainee", "add_trainee"): "Can add trainee",
    ("trainee", "change_trainee"): "Can change trainee",
    ("trainee", "view_trainee"): "Can view trainee",
    ("trainee", "view_trainee_contact"): "Can view trainee contact data",
}


def seed_phase8_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = {}
    for key, name in PERMISSION_NAMES.items():
        model, codename = key
        content_type, _created = ContentType.objects.get_or_create(
            app_label="trainees", model=model
        )
        permission, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions[key] = permission
    for role, keys in ROLE_PERMISSIONS.items():
        group, _created = Group.objects.get_or_create(name=role)
        group.permissions.add(*[permissions[key] for key in sorted(keys)])


def remove_phase8_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(content_type__app_label="trainees")
    for group in Group.objects.filter(name__in=ROLE_PERMISSIONS):
        group.permissions.remove(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("trainees", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_phase8_permissions, remove_phase8_permissions)
    ]
