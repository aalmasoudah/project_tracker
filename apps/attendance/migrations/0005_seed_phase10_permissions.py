from django.db import migrations

ROLE_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {
        ("attendancecorrection", "view_attendancecorrection"),
        ("attendancereview", "view_attendancereview"),
        ("attendancesubmission", "view_all_attendance"),
    },
    "executive_manager": {
        ("attendancecorrection", "view_attendancecorrection"),
        ("attendancereview", "view_attendancereview"),
        ("attendancesubmission", "correct_all_attendance"),
        ("attendancesubmission", "view_all_attendance"),
    },
    "project_manager": {
        ("attendancecorrection", "view_attendancecorrection"),
        ("attendancereview", "view_attendancereview"),
        ("attendancesubmission", "correct_managed_attendance"),
        ("attendancesubmission", "view_managed_attendance"),
    },
    "supervisor": {
        ("attendancecorrection", "view_attendancecorrection"),
        ("attendancereview", "view_attendancereview"),
        ("attendancesubmission", "review_attendance"),
        ("attendancesubmission", "view_supervised_attendance"),
    },
    "employee": set(),
    "contractor": set(),
}


CUSTOM_NAMES = {
    ("attendancesubmission", "correct_all_attendance"): ("Can correct all attendance"),
    ("attendancesubmission", "correct_managed_attendance"): (
        "Can correct managed attendance"
    ),
    ("attendancesubmission", "review_attendance"): ("Can review supervised attendance"),
    ("attendancesubmission", "view_all_attendance"): "Can view all attendance",
    ("attendancesubmission", "view_managed_attendance"): (
        "Can view managed attendance"
    ),
    ("attendancesubmission", "view_supervised_attendance"): (
        "Can view supervised attendance"
    ),
}


def seed_phase10_permissions(apps, schema_editor) -> None:
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


def remove_phase10_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    keys = set().union(*ROLE_PERMISSIONS.values())
    for role, role_keys in ROLE_PERMISSIONS.items():
        group = Group.objects.filter(name=role).first()
        if group is None:
            continue
        for model, codename in role_keys:
            permission = Permission.objects.filter(
                content_type__app_label="attendance",
                content_type__model=model,
                codename=codename,
            ).first()
            if permission is not None:
                group.permissions.remove(permission)
    Permission.objects.filter(
        content_type__app_label="attendance",
        codename__in={codename for _model, codename in keys},
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_phase2_roles"),
        ("attendance", "0004_attendancecorrection_attendancereview_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_phase10_permissions, remove_phase10_permissions)
    ]
