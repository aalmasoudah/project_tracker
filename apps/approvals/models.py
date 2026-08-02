"""Phase 7 milestone and immutable approval-history models."""

from typing import Any, ClassVar

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.accounts.normalization import normalize_account_search
from apps.projects.models import CODE_VALIDATOR


class ProtectedApprovalQuerySet[ModelT: models.Model](models.QuerySet[ModelT]):
    """Reject hard deletion of approval-domain business records."""

    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Approval records cannot be hard-deleted.")


class AppendOnlyDecisionQuerySet(models.QuerySet["ApprovalDecision"]):
    """Reject mutation and deletion of immutable decisions."""

    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise PermissionDenied("Approval decisions are append-only.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Approval decisions cannot be deleted.")


class Milestone(models.Model):
    """A dated project milestone completed only through approval."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        IN_PROGRESS = "in_progress", _("In Progress")
        PENDING_APPROVAL = "pending_approval", _("Pending approval")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    code = models.CharField(_("code"), max_length=30, validators=[CODE_VALIDATOR])
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="milestones",
        verbose_name=_("project"),
    )
    name_ar = models.CharField(_("Arabic name"), max_length=250)
    name_en = models.CharField(_("English name"), max_length=250)
    description = models.TextField(_("description"), blank=True)
    start_date = models.DateField(_("start date"))
    due_date = models.DateField(_("due date"))
    status = models.CharField(
        _("status"),
        max_length=24,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    search_key = models.CharField(max_length=700, editable=False, db_index=True)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)
    archived_at = models.DateTimeField(blank=True, null=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="archived_milestones",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_milestones",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_milestones",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedApprovalQuerySet.as_manager()

    class Meta:
        ordering = ("project__code", "due_date", "code")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("code"),
                name="approvals_milestone_code_ci_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(due_date__gte=models.F("start_date")),
                name="approvals_milestone_dates_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "draft",
                        "in_progress",
                        "pending_approval",
                        "completed",
                        "cancelled",
                    )
                ),
                name="approvals_milestone_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        is_archived=False,
                        archived_at__isnull=True,
                        archived_by__isnull=True,
                    )
                    | models.Q(
                        is_archived=True,
                        archived_at__isnull=False,
                        archived_by__isnull=False,
                    )
                ),
                name="approvals_milestone_archive_state_valid",
            ),
        ]
        permissions = (
            ("view_all_milestones", "Can view all milestones"),
            ("view_managed_milestones", "Can view managed milestones"),
            ("view_context_milestones", "Can view context milestones"),
            ("archive_milestone", "Can archive milestones"),
            ("restore_milestone", "Can restore milestones"),
        )

    def __str__(self) -> str:
        return f"{self.code} - {self.name_en}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.code = self.code.strip().upper()
        self.name_ar = self.name_ar.strip()
        self.name_en = self.name_en.strip()
        project_code = self.project.code if self.project_id else ""
        self.search_key = normalize_account_search(
            f"{self.code} {project_code} {self.name_ar} {self.name_en}"
        )
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        errors = {}
        if self.due_date and self.start_date and self.due_date < self.start_date:
            errors["due_date"] = _("Due date cannot precede start date.")
        if self.project_id:
            project = self.project
            if (
                self.start_date
                and self.due_date
                and (
                    self.start_date < project.start_date
                    or self.due_date > project.end_date
                )
            ):
                errors["due_date"] = _("Milestone dates must be inside project dates.")
        if errors:
            raise ValidationError(errors)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Milestones cannot be hard-deleted.")

    def localized_name(self, language_code: str) -> str:
        return self.name_ar if language_code == "ar" else self.name_en


class ApprovalRequest(models.Model):
    """One immutable-attempt completion request with mutable workflow state."""

    class TargetType(models.TextChoices):
        TASK = "task", _("Task")
        COURSE = "course", _("Course")
        MILESTONE = "milestone", _("Milestone")
        PROJECT = "project", _("Project")

    class Status(models.TextChoices):
        PENDING_SUPERVISOR = "pending_supervisor", _("Pending Supervisor")
        PENDING_MANAGER = "pending_manager", _("Pending Project Manager")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    target_type = models.CharField(
        _("target type"),
        max_length=16,
        choices=TargetType.choices,
        db_index=True,
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.PROTECT,
        related_name="approval_requests",
        blank=True,
        null=True,
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="approval_requests",
        blank=True,
        null=True,
    )
    milestone = models.ForeignKey(
        Milestone,
        on_delete=models.PROTECT,
        related_name="approval_requests",
        blank=True,
        null=True,
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="approval_requests",
        blank=True,
        null=True,
    )
    attempt = models.PositiveIntegerField(_("attempt"))
    status = models.CharField(
        _("status"),
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING_SUPERVISOR,
        db_index=True,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_approval_requests",
    )
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    objects = ProtectedApprovalQuerySet.as_manager()

    class Meta:
        default_permissions = ("view",)
        ordering = ("-submitted_at", "-pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        task__isnull=False,
                        course__isnull=True,
                        milestone__isnull=True,
                        project__isnull=True,
                        target_type="task",
                    )
                    | models.Q(
                        task__isnull=True,
                        course__isnull=False,
                        milestone__isnull=True,
                        project__isnull=True,
                        target_type="course",
                    )
                    | models.Q(
                        task__isnull=True,
                        course__isnull=True,
                        milestone__isnull=False,
                        project__isnull=True,
                        target_type="milestone",
                    )
                    | models.Q(
                        task__isnull=True,
                        course__isnull=True,
                        milestone__isnull=True,
                        project__isnull=False,
                        target_type="project",
                    )
                ),
                name="approvals_request_exactly_one_target",
            ),
            models.CheckConstraint(
                condition=models.Q(attempt__gt=0),
                name="approvals_request_attempt_positive",
            ),
            models.UniqueConstraint(
                fields=("task", "attempt"),
                condition=models.Q(task__isnull=False),
                name="approvals_task_attempt_unique",
            ),
            models.UniqueConstraint(
                fields=("course", "attempt"),
                condition=models.Q(course__isnull=False),
                name="approvals_course_attempt_unique",
            ),
            models.UniqueConstraint(
                fields=("milestone", "attempt"),
                condition=models.Q(milestone__isnull=False),
                name="approvals_milestone_attempt_unique",
            ),
            models.UniqueConstraint(
                fields=("project", "attempt"),
                condition=models.Q(project__isnull=False),
                name="approvals_project_attempt_unique",
            ),
        ]
        permissions = (
            ("view_all_approvals", "Can view all approvals"),
            ("view_managed_approvals", "Can view managed approvals"),
            ("view_context_approvals", "Can view context approvals"),
            ("view_own_approvals", "Can view own approvals"),
            ("submit_approval", "Can submit completion approval"),
            ("decide_supervisor_approval", "Can decide Supervisor approval"),
            ("decide_manager_approval", "Can decide Project Manager approval"),
        )

    def __str__(self) -> str:
        return f"{self.target_type}:{self.target_code}#{self.attempt}"

    @property
    def target(self) -> models.Model:
        if self.task_id:
            task = self.task
            assert task is not None
            return task
        if self.course_id:
            course = self.course
            assert course is not None
            return course
        if self.milestone_id:
            milestone = self.milestone
            assert milestone is not None
            return milestone
        project = self.project
        if project is None:
            raise RuntimeError("Approval request has no target.")
        return project

    @property
    def target_code(self) -> str:
        if self.task_id:
            task = self.task
            assert task is not None
            return task.code
        if self.course_id:
            course = self.course
            assert course is not None
            return course.code
        if self.milestone_id:
            milestone = self.milestone
            assert milestone is not None
            return milestone.code
        project = self.project
        if project is None:
            raise RuntimeError("Approval request has no target.")
        return project.code

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Approval requests cannot be hard-deleted.")


class ApprovalStep(models.Model):
    """One assigned step in a request's fixed two-step sequence."""

    class Role(models.TextChoices):
        SUPERVISOR = "supervisor", _("Supervisor")
        PROJECT_MANAGER = "project_manager", _("Project Manager")

    class Status(models.TextChoices):
        WAITING = "waiting", _("Waiting")
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.PROTECT,
        related_name="steps",
    )
    sequence = models.PositiveSmallIntegerField(_("sequence"))
    role = models.CharField(_("role"), max_length=24, choices=Role.choices)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approval_steps",
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        db_index=True,
    )
    decided_at = models.DateTimeField(blank=True, null=True)

    objects = ProtectedApprovalQuerySet.as_manager()

    class Meta:
        default_permissions = ("view",)
        ordering = ("sequence",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("request", "sequence"),
                name="approvals_step_sequence_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(sequence__in=(1, 2)),
                name="approvals_step_sequence_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.request_id}:{self.sequence}:{self.role}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Approval steps cannot be hard-deleted.")


class ApprovalDecision(models.Model):
    """Append-only decision evidence for one completed step."""

    class Outcome(models.TextChoices):
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    step = models.OneToOneField(
        ApprovalStep,
        on_delete=models.PROTECT,
        related_name="decision",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approval_decisions",
    )
    outcome = models.CharField(_("outcome"), max_length=16, choices=Outcome.choices)
    reason = models.TextField(_("reason"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AppendOnlyDecisionQuerySet.as_manager()

    class Meta:
        default_permissions = ("view",)
        ordering = ("created_at", "pk")

    def __str__(self) -> str:
        return f"{self.step_id}:{self.outcome}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise PermissionDenied("Approval decisions are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Approval decisions cannot be deleted.")
