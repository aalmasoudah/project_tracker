# Generated for the approved Phase 14 audit policy.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0008_alter_auditevent_scope"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="auditevent",
            options={
                "default_permissions": ("view",),
                "ordering": ("-created_at", "-pk"),
                "permissions": (
                    (
                        "view_security_audit",
                        "Can view security and operations audit",
                    ),
                    ("view_business_audit", "Can view business audit"),
                    (
                        "export_security_audit",
                        "Can export security and operations audit",
                    ),
                    ("export_business_audit", "Can export business audit"),
                ),
                "verbose_name": "audit event",
                "verbose_name_plural": "audit events",
            },
        ),
        migrations.AlterField(
            model_name="auditevent",
            name="scope",
            field=models.CharField(
                choices=[
                    ("security", "Security"),
                    ("projects", "Projects"),
                    ("courses", "Courses"),
                    ("tasks", "Tasks"),
                    ("approvals", "Approvals"),
                    ("trainees", "Trainees"),
                    ("attendance", "Attendance"),
                    ("notifications", "Notifications"),
                    ("operations", "Operations"),
                ],
                db_index=True,
                default="security",
                max_length=32,
                verbose_name="scope",
            ),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(
                fields=["scope", "-created_at"],
                name="audit_scope_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(
                fields=["action", "-created_at"],
                name="audit_action_created_idx",
            ),
        ),
    ]
