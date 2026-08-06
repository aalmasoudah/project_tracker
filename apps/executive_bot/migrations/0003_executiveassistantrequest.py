import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

ROLE_PERMISSIONS = {
    "technical_admin": set(),
    "ceo": {"ask_executiveassistant", "view_executiveassistantrequest"},
    "executive_manager": set(),
    "project_manager": set(),
    "supervisor": set(),
    "employee": set(),
    "contractor": set(),
}


def seed_phase19_permissions(apps, schema_editor) -> None:
    del schema_editor
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="executive_bot",
        model="executiveassistantrequest",
    )
    names = {
        "ask_executiveassistant": "Can ask the CEO Telegram AI assistant",
        "view_executiveassistantrequest": "Can view executive assistant request",
    }
    permissions = {}
    for codename, name in names.items():
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


def remove_phase19_permissions(apps, schema_editor) -> None:
    del schema_editor
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(
        content_type__app_label="executive_bot",
        content_type__model="executiveassistantrequest",
        codename__in=(
            "ask_executiveassistant",
            "view_executiveassistantrequest",
        ),
    )
    for group in Group.objects.filter(name__in=ROLE_PERMISSIONS):
        group.permissions.remove(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("executive_bot", "0002_seed_phase16_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExecutiveAssistantRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("chat_id_hash", models.CharField(max_length=64)),
                ("message_key_hash", models.CharField(max_length=64, unique=True)),
                ("question_text", models.CharField(max_length=500)),
                ("question_hash", models.CharField(max_length=64)),
                (
                    "language",
                    models.CharField(
                        choices=[("ar", "Arabic"), ("en", "English")],
                        max_length=2,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("output_data", models.JSONField(blank=True, default=dict)),
                ("provider_code", models.CharField(blank=True, max_length=24)),
                ("model_code", models.CharField(blank=True, max_length=80)),
                ("prompt_version", models.CharField(blank=True, max_length=32)),
                ("source_count", models.PositiveSmallIntegerField(default=0)),
                ("source_truncated", models.BooleanField(default=False)),
                ("input_tokens", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "cached_input_tokens",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("output_tokens", models.PositiveIntegerField(blank=True, null=True)),
                ("failure_code", models.CharField(blank=True, max_length=64)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="executive_assistant_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
                "permissions": (
                    (
                        "ask_executiveassistant",
                        "Can ask the CEO Telegram AI assistant",
                    ),
                ),
                "default_permissions": ("view",),
            },
        ),
        migrations.AddIndex(
            model_name="executiveassistantrequest",
            index=models.Index(
                fields=["requested_by", "-created_at"],
                name="exec_assist_user_created_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="executiveassistantrequest",
            constraint=models.CheckConstraint(
                condition=models.Q(("language__in", ("ar", "en"))),
                name="exec_assist_language_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="executiveassistantrequest",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("status__in", ("queued", "processing", "completed", "failed"))
                ),
                name="exec_assist_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="executiveassistantrequest",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        ("completed_at__isnull", True),
                        ("started_at__isnull", True),
                        ("status", "queued"),
                    )
                    | models.Q(
                        ("completed_at__isnull", True),
                        ("started_at__isnull", False),
                        ("status", "processing"),
                    )
                    | models.Q(
                        ("completed_at__isnull", False),
                        ("started_at__isnull", False),
                        ("status__in", ("completed", "failed")),
                    )
                ),
                name="exec_assist_lifecycle_valid",
            ),
        ),
        migrations.RunPython(seed_phase19_permissions, remove_phase19_permissions),
    ]
