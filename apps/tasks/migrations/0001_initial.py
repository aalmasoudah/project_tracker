from decimal import Decimal

import django.core.validators
import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models

import apps.tasks.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("courses", "0002_seed_phase4_permissions"),
        ("projects", "0002_seed_phase3_permissions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=30,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Use 2-30 uppercase English letters, numbers, underscores, or hyphens, starting with a letter.",
                                regex="^[A-Z][A-Z0-9_-]{1,29}$",
                            )
                        ],
                        verbose_name="code",
                    ),
                ),
                (
                    "name_ar",
                    models.CharField(max_length=100, verbose_name="Arabic name"),
                ),
                (
                    "name_en",
                    models.CharField(max_length=100, verbose_name="English name"),
                ),
                (
                    "search_key",
                    models.CharField(db_index=True, editable=False, max_length=300),
                ),
                (
                    "is_archived",
                    models.BooleanField(
                        db_index=True, default=False, verbose_name="archived"
                    ),
                ),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_task_tags",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="updated_task_tags",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("code",),
                "permissions": (
                    ("archive_tag", "Can archive task tags"),
                    ("restore_tag", "Can restore task tags"),
                ),
            },
        ),
        migrations.CreateModel(
            name="Task",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=30,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Use 2-30 uppercase English letters, numbers, underscores, or hyphens, starting with a letter.",
                                regex="^[A-Z][A-Z0-9_-]{1,29}$",
                            )
                        ],
                        verbose_name="code",
                    ),
                ),
                (
                    "name_ar",
                    models.CharField(max_length=250, verbose_name="Arabic name"),
                ),
                (
                    "name_en",
                    models.CharField(max_length=250, verbose_name="English name"),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="description"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("todo", "To Do"),
                            ("in_progress", "In Progress"),
                            ("blocked", "Blocked"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="todo",
                        max_length=16,
                        verbose_name="status",
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("critical", "Critical"),
                        ],
                        default="medium",
                        max_length=16,
                        verbose_name="priority",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(blank=True, null=True, verbose_name="start date"),
                ),
                (
                    "due_date",
                    models.DateField(blank=True, null=True, verbose_name="due date"),
                ),
                (
                    "estimated_hours",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=9,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0"))
                        ],
                        verbose_name="estimated hours",
                    ),
                ),
                (
                    "actual_hours",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=9,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0"))
                        ],
                        verbose_name="actual hours",
                    ),
                ),
                (
                    "blocking_reason",
                    models.TextField(blank=True, verbose_name="blocking reason"),
                ),
                (
                    "search_key",
                    models.CharField(db_index=True, editable=False, max_length=1000),
                ),
                (
                    "is_archived",
                    models.BooleanField(
                        db_index=True, default=False, verbose_name="archived"
                    ),
                ),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "archived_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="archived_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tasks",
                        to="courses.course",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subtasks",
                        to="tasks.task",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tasks",
                        to="projects.project",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="updated_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("code",),
                "permissions": (
                    ("view_all_tasks", "Can view all tasks"),
                    ("view_managed_tasks", "Can view managed tasks"),
                    ("view_context_tasks", "Can view context tasks"),
                    ("view_assigned_tasks", "Can view assigned tasks"),
                    ("update_assigned_task", "Can update assigned tasks"),
                    ("manage_task_assignments", "Can manage task assignments"),
                    ("comment_task", "Can comment on tasks"),
                    ("upload_task_file", "Can upload task files"),
                    ("archive_task", "Can archive tasks"),
                    ("restore_task", "Can restore tasks"),
                    ("view_task_history", "Can view task history"),
                ),
            },
        ),
        migrations.CreateModel(
            name="TaskAssignment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("is_primary", models.BooleanField(default=False)),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("removed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assigned_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "removed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="removed_task_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assignments",
                        to="tasks.task",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="task_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TaskComment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("body", models.TextField(max_length=5000, verbose_name="comment")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="task_comments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="comments",
                        to="tasks.task",
                    ),
                ),
            ],
            options={
                "ordering": ("created_at", "pk"),
            },
        ),
        migrations.CreateModel(
            name="TaskFile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        max_length=300,
                        upload_to=apps.tasks.models.task_file_upload_path,
                    ),
                ),
                ("original_name", models.CharField(max_length=255)),
                ("size", models.PositiveBigIntegerField()),
                ("content_type", models.CharField(max_length=150)),
                ("sha256", models.CharField(max_length=64)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="files",
                        to="tasks.task",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="uploaded_task_files",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-uploaded_at", "-pk"),
            },
        ),
        migrations.CreateModel(
            name="TaskTag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("removed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "added_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="added_task_tags",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "removed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="removed_task_tags",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tag",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="task_links",
                        to="tasks.tag",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tag_links",
                        to="tasks.task",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="tag",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("code"),
                name="tasks_tag_code_ci_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="tag",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("archived_at__isnull", True), ("is_archived", False)),
                    models.Q(("archived_at__isnull", False), ("is_archived", True)),
                    _connector="OR",
                ),
                name="tasks_tag_archive_state_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("code"),
                name="tasks_task_code_ci_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("course__isnull", True), ("project__isnull", False)),
                    models.Q(("course__isnull", False), ("project__isnull", True)),
                    _connector="OR",
                ),
                name="tasks_task_exactly_one_owner",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("start_date__isnull", True),
                    ("due_date__isnull", True),
                    ("due_date__gte", models.F("start_date")),
                    _connector="OR",
                ),
                name="tasks_task_dates_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("blocking_reason__gt", ""), ("status", "blocked")),
                    models.Q(("status", "blocked"), _negated=True),
                    _connector="OR",
                ),
                name="tasks_task_blocking_reason_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "status__in",
                        ("todo", "in_progress", "blocked", "completed", "cancelled"),
                    )
                ),
                name="tasks_task_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("priority__in", ("low", "medium", "high", "critical"))
                ),
                name="tasks_task_priority_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("archived_at__isnull", True),
                        ("archived_by__isnull", True),
                        ("is_archived", False),
                    ),
                    models.Q(
                        ("archived_at__isnull", False),
                        ("archived_by__isnull", False),
                        ("is_archived", True),
                    ),
                    _connector="OR",
                ),
                name="tasks_task_archive_state_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(("removed_at__isnull", True)),
                fields=("task", "user"),
                name="tasks_assignment_one_active",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_primary", True), ("removed_at__isnull", True)),
                fields=("task",),
                name="tasks_assignment_one_primary",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskassignment",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("removed_at__isnull", True), ("removed_by__isnull", True)
                    ),
                    models.Q(
                        ("removed_at__isnull", False), ("removed_by__isnull", False)
                    ),
                    _connector="OR",
                ),
                name="tasks_assignment_removal_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="tasktag",
            constraint=models.UniqueConstraint(
                condition=models.Q(("removed_at__isnull", True)),
                fields=("task", "tag"),
                name="tasks_tasktag_one_active",
            ),
        ),
        migrations.AddConstraint(
            model_name="tasktag",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("removed_at__isnull", True), ("removed_by__isnull", True)
                    ),
                    models.Q(
                        ("removed_at__isnull", False), ("removed_by__isnull", False)
                    ),
                    _connector="OR",
                ),
                name="tasks_tasktag_removal_valid",
            ),
        ),
    ]
