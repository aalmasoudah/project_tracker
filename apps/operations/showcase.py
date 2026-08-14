"""Rebuild the fictional Arabic KAU/KSU/KKU development showcase."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.color import no_style
from django.db import connection, transaction
from django.db.models import Model, QuerySet
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.roles import (
    CEO,
    CONTRACTOR,
    EMPLOYEE,
    EXECUTIVE_MANAGER,
    PROJECT_MANAGER,
    SUPERVISOR,
    TECHNICAL_ADMIN,
)
from apps.accounts.services import create_account
from apps.approvals.models import Milestone
from apps.approvals.services import (
    approve_request,
    create_milestone,
    reject_request,
    submit_completion,
    update_milestone,
)
from apps.attendance.models import AttendanceEntry, AttendanceReview, Session
from apps.attendance.services import (
    correct_attendance,
    create_sessions,
    issue_trainer_link,
    review_attendance,
    submit_attendance,
)
from apps.courses.models import Course, Trainer
from apps.courses.services import (
    create_course,
    replace_course_trainers,
    save_trainer,
    update_course,
    upload_course_file,
)
from apps.notifications.events import generate_task_deadline_notifications
from apps.organizations.models import Department
from apps.organizations.services import create_department
from apps.projects.models import Category, Client, Project
from apps.projects.services import (
    archive_project,
    create_project,
    replace_project_team,
    save_reference,
    update_project,
)
from apps.tasks.models import Tag, Task
from apps.tasks.services import (
    add_task_comment,
    archive_task,
    create_task,
    replace_task_tags,
    save_tag,
    update_task,
    upload_task_file,
)
from apps.trainees.services import (
    cancel_import,
    confirm_import,
    create_enrollment,
    preview_import,
)
from apps.workspace.models import SavedFilter
from apps.workspace.services import save_filter


@dataclass(frozen=True)
class ShowcaseSummary:
    users: int
    projects: int
    courses: int
    tasks: int
    milestones: int
    trainees: int
    sessions: int
    notifications: int


def _raw_delete(queryset: QuerySet[Any]) -> None:
    queryset._raw_delete(queryset.db)


def _purge_order(models: set[type[Model]]) -> list[type[Model]]:
    """Return child-first model order from concrete database foreign keys."""
    remaining = set(models)
    ordered: list[type[Model]] = []
    while remaining:
        referenced = {
            field.remote_field.model
            for model in remaining
            for field in model._meta.concrete_fields
            if field.is_relation
            and field.remote_field is not None
            and field.remote_field.model in remaining
            and field.remote_field.model is not model
        }
        leaves = sorted(
            (model for model in remaining if model not in referenced),
            key=lambda model: model._meta.label_lower,
        )
        if not leaves:
            labels = ", ".join(sorted(model._meta.label for model in remaining))
            raise RuntimeError(f"Showcase reset found a model cycle: {labels}")
        for model in leaves:
            ordered.append(model)
            remaining.remove(model)
    return ordered


@transaction.atomic
def reset_application_data(
    *,
    keep_username: str = "zx",
    preserve_usernames: tuple[str, ...] = (),
) -> User:
    """Delete development data while preserving verified local identities."""
    preserved_usernames = {keep_username, *preserve_usernames}
    preserved_users = list(
        User.objects.select_for_update().filter(username__in=preserved_usernames)
    )
    found_usernames = {user.username for user in preserved_users}
    missing_usernames = preserved_usernames - found_usernames
    if missing_usernames:
        missing = ", ".join(sorted(missing_usernames))
        raise RuntimeError(
            f"Required retained showcase accounts are missing: {missing}"
        )
    keep = next(user for user in preserved_users if user.username == keep_username)
    if not keep.is_active or not keep.is_superuser:
        raise RuntimeError(
            "The retained technical administrator must be active and superuser."
        )

    for user in preserved_users:
        user.department = None
        user.deactivated_by = None
        if user.pk == keep.pk:
            user.is_staff = True
            user.save(update_fields=("department", "deactivated_by", "is_staff"))
        else:
            user.save(update_fields=("department", "deactivated_by"))

    preserved = {User, Department, Group, Permission, ContentType}
    purge_models: set[type[Model]] = {
        model
        for model in apps.get_models(include_auto_created=False)
        if model not in preserved and model._meta.managed and not model._meta.proxy
    }
    for model in _purge_order(purge_models):
        _raw_delete(model._base_manager.all())

    User.objects.update(deactivated_by=None)
    preserved_ids = [user.pk for user in preserved_users]
    _raw_delete(User.groups.through._base_manager.exclude(user_id__in=preserved_ids))
    _raw_delete(
        User.user_permissions.through._base_manager.exclude(user_id__in=preserved_ids)
    )
    _raw_delete(User.objects.exclude(pk__in=preserved_ids))
    _raw_delete(Department._base_manager.all())

    keep.groups.set([Group.objects.get(name=TECHNICAL_ADMIN)])
    sequence_models: list[type[Model]] = [*purge_models, User, Department]
    with connection.cursor() as cursor:
        for statement in connection.ops.sequence_reset_sql(no_style(), sequence_models):
            cursor.execute(statement)
    return keep


def _make_account(
    *,
    actor: User,
    department: Department,
    username: str,
    display_name: str,
    role: str,
    password: str,
    must_change_password: bool = False,
) -> User:
    user = create_account(
        actor=actor,
        username=username,
        email=f"{username}@demo.insight.local",
        display_name=display_name,
        department=department,
        role_code=role,
        preferred_language=User.Language.ARABIC,
        temporary_password=password,
    )
    if user.must_change_password != must_change_password:
        user.must_change_password = must_change_password
        user.save(update_fields=("must_change_password",))
    return user


def _set_project_status(actor: User, project: Project, status: str) -> Project:
    return update_project(
        actor=actor,
        project=project,
        code=project.code,
        name_ar=project.name_ar,
        name_en=project.name_en,
        department=project.department,
        client=project.client,
        category=project.category,
        manager=project.manager,
        supervisor=project.supervisor,
        status=status,
        priority=project.priority,
        start_date=project.start_date,
        end_date=project.end_date,
        budget=project.budget,
        goals=project.goals,
        requirements=project.requirements,
        notes=project.notes,
    )


def _set_course_status(actor: User, course: Course, status: str) -> Course:
    return update_course(
        actor=actor,
        course=course,
        code=course.code,
        project=course.project,
        name_ar=course.name_ar,
        name_en=course.name_en,
        description=course.description,
        delivery_type=course.delivery_type,
        location=course.location,
        capacity=course.capacity,
        start_at=course.start_at,
        end_at=course.end_at,
        status=status,
        notes=course.notes,
    )


def _set_task_status(
    actor: User,
    task: Task,
    status: str,
    *,
    blocking_reason: str | None = None,
) -> Task:
    return update_task(
        actor=actor,
        task=task,
        code=task.code,
        project=task.project,
        course=task.course,
        parent=task.parent,
        name_ar=task.name_ar,
        name_en=task.name_en,
        description=task.description,
        status=status,
        priority=task.priority,
        start_date=task.start_date,
        due_date=task.due_date,
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours,
        blocking_reason=(
            task.blocking_reason if blocking_reason is None else blocking_reason
        ),
    )


def _create_task_with_state(
    *,
    actor: User,
    code: str,
    name_ar: str,
    name_en: str,
    project: Project | None,
    course: Course | None,
    parent: Task | None,
    assignees: list[User],
    primary: User,
    priority: str,
    start_date: date,
    due_date: date,
    final_status: str,
    tags: list[Tag],
    blocking_reason: str = "",
) -> Task:
    task = create_task(
        actor=actor,
        assignees=assignees,
        primary_owner=primary,
        code=code,
        project=project,
        course=course,
        parent=parent,
        name_ar=name_ar,
        name_en=name_en,
        description=f"سيناريو عرض خيالي للمهمة {name_ar}.",
        status=Task.Status.TODO,
        priority=priority,
        start_date=start_date,
        due_date=due_date,
        estimated_hours=Decimal("24.00"),
        actual_hours=Decimal("0.00"),
        blocking_reason="",
    )
    if final_status in {
        Task.Status.IN_PROGRESS,
        Task.Status.BLOCKED,
        Task.Status.COMPLETED,
    }:
        task = _set_task_status(actor, task, Task.Status.IN_PROGRESS)
    if final_status == Task.Status.BLOCKED:
        task = _set_task_status(
            actor,
            task,
            Task.Status.BLOCKED,
            blocking_reason=blocking_reason,
        )
    elif final_status == Task.Status.COMPLETED:
        task = _set_task_status(actor, task, Task.Status.COMPLETED)
    elif final_status == Task.Status.CANCELLED:
        task = _set_task_status(actor, task, Task.Status.CANCELLED)
    replace_task_tags(actor=actor, task=task, tags=tags)
    return task


def _riyadh_datetime(day: date, hour: int) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour=hour)))


def _pdf_upload(filename: str) -> SimpleUploadedFile:
    content = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n"
    return SimpleUploadedFile(filename, content, content_type="application/pdf")


def _seed_attendance(
    *,
    executive: User,
    courses: dict[str, Course],
    trainers: dict[str, Trainer],
    supervisors: dict[str, User],
    today: date,
) -> None:
    values: list[str] = [
        str(AttendanceEntry.Value.PRESENT),
        str(AttendanceEntry.Value.LATE),
        str(AttendanceEntry.Value.ABSENT),
        str(AttendanceEntry.Value.EXCUSED),
    ]
    submissions: dict[str, Any] = {}
    for index, university in enumerate(("KAU", "KSU", "KKU")):
        course = courses[university]
        session = create_sessions(
            actor=executive,
            course=course,
            trainer=trainers[university],
            title_ar=f"جلسة التطبيق العملي - {university}",
            title_en=f"Practical workshop - {university}",
            start_at=_riyadh_datetime(today - timedelta(days=2 + index), 10),
            end_at=_riyadh_datetime(today - timedelta(days=2 + index), 12),
            notes="جلسة خيالية لاختبار الحضور والمراجعة.",
        )[0]
        link, _token = issue_trainer_link(
            actor=executive,
            session=session,
            lifetime_hours=24,
        )
        participants = list(session.participants.order_by("pk"))
        entries: dict[int, tuple[str, str]] = {
            participant.pk: (values[offset % len(values)], "ملاحظة عرض خيالية")
            for offset, participant in enumerate(participants, start=index)
        }
        submissions[university] = submit_attendance(
            link=link,
            entries=entries,
            trainer_notes="تم توثيق الحضور ضمن سيناريو العرض.",
            evidence_files=(
                [_pdf_upload("kau-attendance-evidence.pdf")]
                if university == "KAU"
                else []
            ),
        )

    kau = review_attendance(
        actor=supervisors["KAU"],
        submission=submissions["KAU"],
        decision=AttendanceReview.Decision.APPROVED,
    )
    corrected = {
        entry.participant_id: (
            AttendanceEntry.Value.LATE if index == 0 else entry.value,
            "تصحيح معتمد لأغراض العرض" if index == 0 else entry.notes,
        )
        for index, entry in enumerate(kau.entries.order_by("participant_id"))
    }
    correct_attendance(
        actor=executive,
        submission=kau,
        entries=corrected,
        reason="تصحيح خيالي لإظهار سجل التعديلات المعتمد.",
    )

    kku = review_attendance(
        actor=supervisors["KKU"],
        submission=submissions["KKU"],
        decision=AttendanceReview.Decision.REJECTED,
        reason="يلزم توضيح حالة أحد المتدربين قبل الاعتماد.",
    )
    resubmission_entries = {
        entry.participant_id: (entry.value, "تم التوضيح بعد الرفض")
        for entry in kku.entries.order_by("participant_id")
    }
    submit_attendance(
        link=kku.trainer_link,
        entries=resubmission_entries,
        trainer_notes="أعيد الإرسال بعد معالجة سبب الرفض.",
        evidence_files=[],
    )

    create_sessions(
        actor=executive,
        course=courses["KAU"],
        trainer=trainers["KAU"],
        title_ar="جلسات المتابعة الأسبوعية",
        title_en="Weekly follow-up sessions",
        start_at=_riyadh_datetime(today + timedelta(days=7), 10),
        end_at=_riyadh_datetime(today + timedelta(days=7), 11),
        recurrence=Session.Recurrence.WEEKLY,
        recurrence_count=3,
    )


@transaction.atomic
def build_university_showcase(
    *, password: str, keep_username: str = "zx"
) -> ShowcaseSummary:
    """Reset and create one coherent fictional full-feature development dataset."""
    if len(password) < 12:
        raise ValueError("The demo password must contain at least 12 characters.")
    technical = reset_application_data(keep_username=keep_username)
    today = timezone.localdate()
    start = today - timedelta(days=90)
    end = today + timedelta(days=180)

    department = create_department(
        actor=technical,
        code="UNI-PMO",
        name_ar="مكتب إدارة البرامج الجامعية",
        name_en="University Programs PMO",
    )
    accounts = {
        "CEO": ("demo.executive", "نورة الحربي - الرئيس التنفيذي", CEO),
        "EXEC": (
            "demo.exec.manager",
            "سلمان القحطاني - المدير التنفيذي",
            EXECUTIVE_MANAGER,
        ),
        "KAU_PM": ("demo.pm.kau", "ريم الغامدي - مدير برنامج KAU", PROJECT_MANAGER),
        "KSU_PM": ("demo.pm.ksu", "خالد العتيبي - مدير برنامج KSU", PROJECT_MANAGER),
        "KKU_PM": ("demo.pm.kku", "سارة الشهراني - مدير برنامج KKU", PROJECT_MANAGER),
        "KAU_SUP": ("demo.supervisor.kau", "عمر الزهراني - مشرف KAU", SUPERVISOR),
        "KSU_SUP": ("demo.supervisor.ksu", "هند المطيري - مشرف KSU", SUPERVISOR),
        "KKU_SUP": ("demo.supervisor.kku", "ماجد الأسمري - مشرف KKU", SUPERVISOR),
        "ANALYST": ("demo.shared.analyst", "ليان الشريف - محلل مشترك", EMPLOYEE),
        "QA": ("demo.shared.qa", "عبدالله السلمي - ضمان جودة مشترك", EMPLOYEE),
        "KAU_SPEC": ("demo.kau.specialist", "جود العمري - أخصائي KAU", EMPLOYEE),
        "KSU_SPEC": ("demo.ksu.specialist", "تركي الدوسري - أخصائي KSU", EMPLOYEE),
        "KKU_SPEC": ("demo.kku.specialist", "شهد القحطاني - أخصائي KKU", EMPLOYEE),
        "DESIGN": ("demo.shared.designer", "رزان المالكي - مصمم متعاقد", CONTRACTOR),
        "NEW": ("demo.new.employee", "موظف جديد - اختبار تغيير كلمة المرور", EMPLOYEE),
    }
    users = {
        key: _make_account(
            actor=technical,
            department=department,
            username=username,
            display_name=display,
            role=role,
            password=password,
            must_change_password=key == "NEW",
        )
        for key, (username, display, role) in accounts.items()
    }
    executive = users["EXEC"]

    clients = {
        "KAU": save_reference(
            actor=executive,
            model=Client,
            code="KAU",
            name_ar="جامعة الملك عبدالعزيز",
            name_en="King Abdulaziz University",
        ),
        "KSU": save_reference(
            actor=executive,
            model=Client,
            code="KSU",
            name_ar="جامعة الملك سعود",
            name_en="King Saud University",
        ),
        "KKU": save_reference(
            actor=executive,
            model=Client,
            code="KKU",
            name_ar="جامعة الملك خالد",
            name_en="King Khalid University",
        ),
    }
    categories = {
        "KAU": save_reference(
            actor=executive,
            model=Category,
            code="KAU-DX",
            name_ar="برنامج التحول الرقمي للخدمات الجامعية",
            name_en="University Services Digital Transformation Program",
        ),
        "KSU": save_reference(
            actor=executive,
            model=Category,
            code="KSU-RI",
            name_ar="برنامج تمكين البحث والابتكار",
            name_en="Research and Innovation Enablement Program",
        ),
        "KKU": save_reference(
            actor=executive,
            model=Category,
            code="KKU-SX",
            name_ar="برنامج تطوير تجربة الطالب",
            name_en="Student Experience Development Program",
        ),
    }
    project_specs = (
        (
            "KAU-PORTAL",
            "بوابة الخدمات الطلابية الذكية",
            "Smart Student Services Portal",
            "KAU",
            "KAU_PM",
            "KAU_SUP",
            Project.Priority.CRITICAL,
            "active",
            Decimal("1850000.00"),
        ),
        (
            "KAU-DATA",
            "منصة حوكمة البيانات",
            "Data Governance Platform",
            "KAU",
            "KAU_PM",
            "KAU_SUP",
            Project.Priority.HIGH,
            "on_hold",
            Decimal("980000.00"),
        ),
        (
            "KSU-RESEARCH",
            "منصة إدارة المنح البحثية",
            "Research Grants Platform",
            "KSU",
            "KSU_PM",
            "KSU_SUP",
            Project.Priority.HIGH,
            "active",
            Decimal("1420000.00"),
        ),
        (
            "KSU-AILAB",
            "جاهزية مختبرات الذكاء الاصطناعي",
            "AI Labs Readiness",
            "KSU",
            "KSU_PM",
            "KSU_SUP",
            Project.Priority.CRITICAL,
            "active",
            Decimal("2100000.00"),
        ),
        (
            "KKU-JOURNEY",
            "رحلة الطالب الرقمية",
            "Digital Student Journey",
            "KKU",
            "KKU_PM",
            "KKU_SUP",
            Project.Priority.HIGH,
            "active",
            Decimal("1275000.00"),
        ),
        (
            "KKU-SKILLS",
            "أكاديمية المهارات المستقبلية",
            "Future Skills Academy",
            "KKU",
            "KKU_PM",
            "KKU_SUP",
            Project.Priority.MEDIUM,
            "draft",
            Decimal("760000.00"),
        ),
    )
    projects: dict[str, Project] = {}
    for (
        code,
        name_ar,
        name_en,
        uni,
        manager_key,
        supervisor_key,
        priority,
        state,
        budget,
    ) in project_specs:
        project = create_project(
            actor=executive,
            code=code,
            name_ar=name_ar,
            name_en=name_en,
            department=department,
            client=clients[uni],
            category=categories[uni],
            manager=users[manager_key],
            supervisor=users[supervisor_key],
            status=Project.Status.DRAFT,
            priority=priority,
            start_date=start,
            end_date=end,
            budget=budget,
            goals="تقديم نتيجة قابلة للقياس وتحسين تجربة المستفيد ضمن بيانات خيالية.",
            requirements=(
                "أمن المعلومات، سهولة الاستخدام، التكامل، والتقارير التنفيذية."
            ),
            notes="هذا مشروع عرض خيالي ولا يحتوي بيانات جامعة حقيقية.",
        )
        if state in {"active", "on_hold"}:
            project = _set_project_status(executive, project, Project.Status.ACTIVE)
        if state == "on_hold":
            project = _set_project_status(executive, project, Project.Status.ON_HOLD)
        projects[code] = project

    legacy = create_project(
        actor=executive,
        code="KAU-LEGACY",
        name_ar="تجربة بوابة سابقة مؤرشفة",
        name_en="Archived Legacy Portal Pilot",
        department=department,
        client=clients["KAU"],
        category=categories["KAU"],
        manager=users["KAU_PM"],
        supervisor=users["KAU_SUP"],
        status=Project.Status.DRAFT,
        priority=Project.Priority.LOW,
        start_date=start,
        end_date=end,
        budget=Decimal("120000.00"),
        goals="إظهار مركز الأرشيف.",
        requirements="لا يوجد.",
        notes="سجل خيالي مؤرشف.",
    )
    archive_project(actor=executive, project=legacy)

    shared_members = [users["ANALYST"], users["QA"], users["DESIGN"]]
    university_member = {
        "KAU": users["KAU_SPEC"],
        "KSU": users["KSU_SPEC"],
        "KKU": users["KKU_SPEC"],
    }
    for project in projects.values():
        uni = project.code.split("-", 1)[0]
        replace_project_team(
            actor=executive,
            project=project,
            members=[*shared_members, university_member[uni]],
        )

    tags = {
        "urgent": save_tag(
            actor=executive, code="URGENT", name_ar="عاجل", name_en="Urgent"
        ),
        "integration": save_tag(
            actor=executive, code="INTEGRATION", name_ar="تكامل", name_en="Integration"
        ),
        "quality": save_tag(
            actor=executive, code="QUALITY", name_ar="جودة", name_en="Quality"
        ),
        "training": save_tag(
            actor=executive, code="TRAINING", name_ar="تدريب", name_en="Training"
        ),
        "security": save_tag(
            actor=executive,
            code="SECURITY",
            name_ar="أمن سيبراني",
            name_en="Cybersecurity",
        ),
    }

    task_groups: dict[str, list[Task]] = {}
    active_projects = [
        project
        for project in projects.values()
        if project.status == Project.Status.ACTIVE
    ]
    unique_names = {
        "KAU": ("تكامل الهوية الرقمية للطالب", "Student digital identity integration"),
        "KSU": ("ربط بيانات المختبرات البحثية", "Research laboratory data integration"),
        "KKU": (
            "تحليل نقاط التعثر في رحلة الطالب",
            "Student journey friction analysis",
        ),
    }
    for project in active_projects:
        uni = project.code.split("-", 1)[0]
        prefix = project.code.replace("-", "")[:10]
        specialist = university_member[uni]
        parent = _create_task_with_state(
            actor=executive,
            code=f"{prefix}-PLAN",
            name_ar="إطلاق حزمة العمل",
            name_en="Work package delivery",
            project=project,
            course=None,
            parent=None,
            assignees=[users["ANALYST"], specialist],
            primary=users["ANALYST"],
            priority=Task.Priority.HIGH,
            start_date=today - timedelta(days=45),
            due_date=today + timedelta(days=45),
            final_status=Task.Status.IN_PROGRESS,
            tags=[tags["quality"]],
        )
        completed = _create_task_with_state(
            actor=executive,
            code=f"{prefix}-REQ",
            name_ar="اعتماد المتطلبات",
            name_en="Requirements sign-off",
            project=project,
            course=None,
            parent=parent,
            assignees=[specialist, users["ANALYST"]],
            primary=specialist,
            priority=Task.Priority.MEDIUM,
            start_date=today - timedelta(days=40),
            due_date=today - timedelta(days=25),
            final_status=Task.Status.COMPLETED,
            tags=[tags["quality"]],
        )
        blocked = _create_task_with_state(
            actor=executive,
            code=f"{prefix}-INT",
            name_ar="تنفيذ التكامل الرئيسي",
            name_en="Core integration",
            project=project,
            course=None,
            parent=parent,
            assignees=[specialist, users["QA"]],
            primary=specialist,
            priority=Task.Priority.CRITICAL,
            start_date=today - timedelta(days=25),
            due_date=today - timedelta(days=5),
            final_status=Task.Status.BLOCKED,
            blocking_reason="بانتظار اعتماد واجهة التكامل من الجهة المالكة.",
            tags=[tags["urgent"], tags["integration"]],
        )
        due = _create_task_with_state(
            actor=executive,
            code=f"{prefix}-QA",
            name_ar="اختبار القبول والأمان",
            name_en="Acceptance and security testing",
            project=project,
            course=None,
            parent=None,
            assignees=[users["QA"], specialist],
            primary=users["QA"],
            priority=Task.Priority.CRITICAL,
            start_date=today - timedelta(days=3),
            due_date=today + timedelta(days=1),
            final_status=Task.Status.TODO,
            tags=[tags["urgent"], tags["quality"], tags["security"]],
        )
        unique = _create_task_with_state(
            actor=executive,
            code=f"{prefix}-UNI",
            name_ar=unique_names[uni][0],
            name_en=unique_names[uni][1],
            project=project,
            course=None,
            parent=None,
            assignees=[specialist, users["DESIGN"]],
            primary=specialist,
            priority=Task.Priority.HIGH,
            start_date=today - timedelta(days=10),
            due_date=today + timedelta(days=20),
            final_status=Task.Status.IN_PROGRESS,
            tags=[tags["integration"]],
        )
        cancelled = _create_task_with_state(
            actor=executive,
            code=f"{prefix}-CR",
            name_ar="طلب تغيير خارج النطاق",
            name_en="Out-of-scope change request",
            project=project,
            course=None,
            parent=None,
            assignees=[users["ANALYST"]],
            primary=users["ANALYST"],
            priority=Task.Priority.LOW,
            start_date=today - timedelta(days=20),
            due_date=today + timedelta(days=60),
            final_status=Task.Status.CANCELLED,
            tags=[tags["quality"]],
        )
        add_task_comment(
            actor=specialist,
            task=blocked,
            body=(
                "تحتاج نقطة التكامل إلى قرار. @demo.shared.analyst "
                "يرجى تحديث خطة التعافي."
            ),
        )
        add_task_comment(
            actor=users["QA"],
            task=due,
            body="تم تجهيز حالات الاختبار العربية والإنجليزية للجوال وسطح المكتب.",
        )
        upload_task_file(
            actor=executive,
            task=unique,
            upload=_pdf_upload(f"{project.code.lower()}-requirements.pdf"),
        )
        task_groups[project.code] = [parent, completed, blocked, due, unique, cancelled]

    archived_task = _create_task_with_state(
        actor=executive,
        code="KAUDATA-OLD",
        name_ar="تحليل قديم مؤرشف",
        name_en="Archived analysis task",
        project=projects["KAU-DATA"],
        course=None,
        parent=None,
        assignees=[users["KAU_SPEC"]],
        primary=users["KAU_SPEC"],
        priority=Task.Priority.LOW,
        start_date=today - timedelta(days=30),
        due_date=today + timedelta(days=30),
        final_status=Task.Status.TODO,
        tags=[tags["quality"]],
    )
    archive_task(actor=executive, task=archived_task)

    trainer_specs = {
        "KAU": ("TR-KAU", "د. أمل الزهراني", "Dr Amal Alzahrani"),
        "KSU": ("TR-KSU", "د. فيصل الدوسري", "Dr Faisal Aldosari"),
        "KKU": ("TR-KKU", "د. منى الأسمري", "Dr Mona Alasmari"),
    }
    trainers = {
        uni: save_trainer(
            actor=executive,
            code=code,
            name_ar=name_ar,
            name_en=name_en,
            email=f"trainer.{uni.lower()}@demo.insight.local",
            phone=f"+966500000{index:03d}",
            organization=clients[uni].name_ar,
            notes="مدرب خيالي مخصص لسيناريو العرض.",
        )
        for index, (uni, (code, name_ar, name_en)) in enumerate(
            trainer_specs.items(), start=1
        )
    }
    primary_projects = {
        "KAU": projects["KAU-PORTAL"],
        "KSU": projects["KSU-RESEARCH"],
        "KKU": projects["KKU-JOURNEY"],
    }
    delivery = {
        "KAU": Course.DeliveryType.HYBRID,
        "KSU": Course.DeliveryType.ONLINE,
        "KKU": Course.DeliveryType.IN_PERSON,
    }
    courses: dict[str, Course] = {}
    for uni, project in primary_projects.items():
        course = create_course(
            actor=executive,
            code=f"{uni}-ENABLE",
            project=project,
            name_ar=f"برنامج تمكين فريق {uni}",
            name_en=f"{uni} Team Enablement",
            description="دورة خيالية لربط التدريب بالتنفيذ والمتابعة.",
            delivery_type=delivery[uni],
            location="الرياض / عن بُعد",
            capacity=20,
            start_at=_riyadh_datetime(today - timedelta(days=45), 8),
            end_at=_riyadh_datetime(today + timedelta(days=90), 16),
            status=Course.Status.DRAFT,
            notes="تشمل حضورًا واعتمادًا وتقارير عربية.",
        )
        course = _set_course_status(executive, course, Course.Status.ACTIVE)
        replace_course_trainers(
            actor=executive, course=course, trainers=[trainers[uni]]
        )
        upload_course_file(
            actor=executive,
            course=course,
            upload=_pdf_upload(f"{uni.lower()}-course-guide.pdf"),
        )
        courses[uni] = course
        _create_task_with_state(
            actor=executive,
            code=f"{uni}COURSE-PREP",
            name_ar="تجهيز المحتوى التدريبي",
            name_en="Prepare training content",
            project=None,
            course=course,
            parent=None,
            assignees=[university_member[uni], users["ANALYST"]],
            primary=university_member[uni],
            priority=Task.Priority.MEDIUM,
            start_date=today - timedelta(days=35),
            due_date=today - timedelta(days=15),
            final_status=Task.Status.COMPLETED,
            tags=[tags["training"]],
        )
        _create_task_with_state(
            actor=executive,
            code=f"{uni}COURSE-FOLLOW",
            name_ar="متابعة تطبيق المتدربين",
            name_en="Trainee application follow-up",
            project=None,
            course=course,
            parent=None,
            assignees=[university_member[uni], users["QA"]],
            primary=university_member[uni],
            priority=Task.Priority.HIGH,
            start_date=today - timedelta(days=5),
            due_date=today + timedelta(days=25),
            final_status=Task.Status.IN_PROGRESS,
            tags=[tags["training"], tags["quality"]],
        )

    trainee_names = {
        "KAU": (
            "سارة أحمد الغامدي",
            "عبدالله محمد الزهراني",
            "نورة خالد الحربي",
            "فيصل علي القرني",
        ),
        "KSU": (
            "ريم سعد العتيبي",
            "محمد عبدالعزيز الدوسري",
            "لمى فهد القحطاني",
            "تركي صالح المطيري",
        ),
        "KKU": (
            "أروى حسن الشهري",
            "خالد عبدالله الأسمري",
            "هدى علي القحطاني",
            "ماجد أحمد عسيري",
        ),
    }

    for index, (kau_name, kku_name) in enumerate(
        zip(trainee_names["KAU"], trainee_names["KKU"], strict=True),
        start=1,
    ):
        create_enrollment(
            actor=executive,
            course=courses["KAU"],
            full_name=kau_name,
            phone=f"0501000{index:03d}",
            email=f"kau.trainee{index}@example.test",
        )
        create_enrollment(
            actor=executive,
            course=courses["KKU"],
            full_name=kku_name,
            phone=f"0503000{index:03d}",
            email=f"kku.trainee{index}@example.test",
        )

    csv_text = "الاسم الكامل,رقم الجوال,البريد الإلكتروني\n" + "\n".join(
        f"{full_name},0502000{index:03d},ksu.trainee{index}@example.test"
        for index, full_name in enumerate(trainee_names["KSU"], start=1)
    )
    batch = preview_import(
        actor=executive,
        course=courses["KSU"],
        upload=SimpleUploadedFile(
            "ksu-trainees-ar.csv",
            csv_text.encode("utf-8-sig"),
            content_type="text/csv",
        ),
    )
    confirm_import(actor=executive, batch=batch)
    cancelled_batch = preview_import(
        actor=executive,
        course=courses["KKU"],
        upload=SimpleUploadedFile(
            "kku-preview-cancelled.csv",
            (
                "full_name,phone,email\nمتدرب معاينة,0503999999,preview@example.test\n"
            ).encode(),
            content_type="text/csv",
        ),
    )
    cancel_import(actor=executive, batch=cancelled_batch)

    _seed_attendance(
        executive=executive,
        courses=courses,
        trainers=trainers,
        supervisors={
            "KAU": users["KAU_SUP"],
            "KSU": users["KSU_SUP"],
            "KKU": users["KKU_SUP"],
        },
        today=today,
    )

    milestone_specs = (
        (
            "KAU-GATE",
            primary_projects["KAU"],
            "اعتماد بوابة الإطلاق",
            "Launch readiness gate",
            users["KAU_SUP"],
            users["KAU_PM"],
            "approved",
        ),
        (
            "KSU-GATE",
            primary_projects["KSU"],
            "اعتماد تكامل البحث",
            "Research integration gate",
            users["KSU_SUP"],
            users["KSU_PM"],
            "rejected",
        ),
        (
            "KKU-GATE",
            primary_projects["KKU"],
            "اعتماد تجربة الطالب",
            "Student journey gate",
            users["KKU_SUP"],
            users["KKU_PM"],
            "pending_manager",
        ),
    )
    for (
        code,
        project,
        name_ar,
        name_en,
        supervisor,
        manager,
        outcome,
    ) in milestone_specs:
        milestone = create_milestone(
            actor=executive,
            code=code,
            project=project,
            name_ar=name_ar,
            name_en=name_en,
            description="بوابة قرار خيالية لإظهار مسار الاعتماد المتسلسل.",
            start_date=today - timedelta(days=10),
            due_date=today + timedelta(days=10),
            status=Milestone.Status.DRAFT,
        )
        milestone = update_milestone(
            actor=executive,
            milestone=milestone,
            code=milestone.code,
            project=milestone.project,
            name_ar=milestone.name_ar,
            name_en=milestone.name_en,
            description=milestone.description,
            start_date=milestone.start_date,
            due_date=milestone.due_date,
            status=Milestone.Status.IN_PROGRESS,
        )
        approval = submit_completion(actor=executive, target=milestone)
        if outcome == "rejected":
            reject_request(
                actor=supervisor,
                approval_request=approval,
                reason="يلزم استكمال دليل الاختبار قبل الاعتماد.",
            )
        else:
            approval = approve_request(actor=supervisor, approval_request=approval)
            if outcome == "approved":
                approve_request(actor=manager, approval_request=approval)

    save_filter(
        owner=users["CEO"],
        name="المهام الحرجة والمتأخرة",
        view_type=SavedFilter.ViewType.KANBAN,
        criteria={"q": "تكامل"},
    )
    save_filter(
        owner=users["EXEC"],
        name="خطة البرامج القادمة",
        view_type=SavedFilter.ViewType.GANTT,
        criteria={
            "date_from": today.isoformat(),
            "date_to": (today + timedelta(days=60)).isoformat(),
        },
    )
    save_filter(
        owner=users["ANALYST"],
        name="بحث البرامج الجامعية",
        view_type=SavedFilter.ViewType.SEARCH,
        criteria={"q": "جامعة"},
    )
    generate_task_deadline_notifications(today=today)

    from apps.notifications.models import Notification
    from apps.trainees.models import Trainee

    return ShowcaseSummary(
        users=User.objects.count(),
        projects=Project.objects.count(),
        courses=Course.objects.count(),
        tasks=Task.objects.count(),
        milestones=Milestone.objects.count(),
        trainees=Trainee.objects.count(),
        sessions=Session.objects.count(),
        notifications=Notification.objects.count(),
    )


@transaction.atomic
def build_minimal_feature_showcase(
    *,
    password: str,
    keep_username: str = "zx",
    ceo_username: str = "demo.executive",
) -> ShowcaseSummary:
    """Build one compact Arabic scenario spanning every implemented domain."""
    if len(password) < 12:
        raise ValueError("The demo password must contain at least 12 characters.")

    technical = reset_application_data(
        keep_username=keep_username,
        preserve_usernames=(ceo_username,),
    )
    ceo = User.objects.select_for_update().get(username=ceo_username)
    if not ceo.is_active:
        raise RuntimeError("The retained Telegram CEO account must be active.")

    today = timezone.localdate()
    start = today - timedelta(days=60)
    end = today + timedelta(days=180)
    department = create_department(
        actor=technical,
        code="DEMO-PMO",
        name_ar="مكتب إدارة مشروع العرض المتكامل",
        name_en="Integrated Showcase PMO",
    )

    ceo.display_name = "نورة الحربي - الرئيس التنفيذي"
    ceo.department = department
    ceo.preferred_language = User.Language.ARABIC
    ceo.must_change_password = False
    ceo.groups.set([Group.objects.get(name=CEO)])
    ceo.save(
        update_fields=(
            "display_name",
            "department",
            "preferred_language",
            "must_change_password",
        )
    )

    account_specs = {
        "EXEC": (
            "demo.exec.manager",
            "سلمان القحطاني - المدير التنفيذي",
            EXECUTIVE_MANAGER,
        ),
        "PM": (
            "demo.pm.kau",
            "ريم الغامدي - مدير المشروع",
            PROJECT_MANAGER,
        ),
        "SUP": (
            "demo.supervisor.kau",
            "عمر الزهراني - مشرف المشروع",
            SUPERVISOR,
        ),
        "EMP": (
            "demo.employee",
            "ليان الشريف - موظفة تنفيذ",
            EMPLOYEE,
        ),
        "CONTRACTOR": (
            "demo.contractor",
            "رزان المالكي - متعاقدة تجربة مستخدم",
            CONTRACTOR,
        ),
    }
    users = {
        key: _make_account(
            actor=technical,
            department=department,
            username=username,
            display_name=display_name,
            role=role,
            password=password,
        )
        for key, (username, display_name, role) in account_specs.items()
    }
    executive = users["EXEC"]
    manager = users["PM"]
    supervisor = users["SUP"]
    employee = users["EMP"]
    contractor = users["CONTRACTOR"]

    client = save_reference(
        actor=executive,
        model=Client,
        code="KAU-DEMO",
        name_ar="جامعة الملك عبدالعزيز - بيانات عرض خيالية",
        name_en="King Abdulaziz University - Fictional Demo",
    )
    category = save_reference(
        actor=executive,
        model=Category,
        code="DIGITAL-EXPERIENCE",
        name_ar="التحول الرقمي وتجربة المستفيد",
        name_en="Digital Transformation and User Experience",
    )
    project = create_project(
        actor=executive,
        code="DEMO-360",
        name_ar="منصة الخدمات الجامعية الذكية - العرض المتكامل",
        name_en="Smart University Services - Complete Showcase",
        department=department,
        client=client,
        category=category,
        manager=manager,
        supervisor=supervisor,
        status=Project.Status.DRAFT,
        priority=Project.Priority.CRITICAL,
        start_date=start,
        end_date=end,
        budget=Decimal("950000.00"),
        goals=(
            "عرض إدارة المشروع والمهام والتدريب والحضور والموافقات والتقارير "
            "والذكاء الاصطناعي في سيناريو واحد."
        ),
        requirements=(
            "دعم العربية والإنجليزية، صلاحيات دقيقة، تقارير قابلة للتنزيل، "
            "ومخرجات ذكاء اصطناعي موثقة."
        ),
        notes="جميع الأسماء والبيانات في هذا المشروع خيالية ومخصصة للاختبار المحلي.",
    )
    project = _set_project_status(executive, project, Project.Status.ACTIVE)
    replace_project_team(
        actor=executive,
        project=project,
        members=[employee, contractor],
    )

    archived_project = create_project(
        actor=executive,
        code="DEMO-ARCHIVE",
        name_ar="تجربة سابقة مؤرشفة",
        name_en="Archived Previous Pilot",
        department=department,
        client=client,
        category=category,
        manager=manager,
        supervisor=supervisor,
        status=Project.Status.DRAFT,
        priority=Project.Priority.LOW,
        start_date=start,
        end_date=end,
        budget=Decimal("50000.00"),
        goals="إظهار مركز الأرشيف والاستعادة.",
        requirements="لا يوجد.",
        notes="سجل خيالي مؤرشف للاختبار.",
    )
    archive_project(actor=executive, project=archived_project)

    tags = {
        "urgent": save_tag(
            actor=executive,
            code="URGENT",
            name_ar="عاجل",
            name_en="Urgent",
        ),
        "quality": save_tag(
            actor=executive,
            code="QUALITY",
            name_ar="جودة",
            name_en="Quality",
        ),
        "training": save_tag(
            actor=executive,
            code="TRAINING",
            name_ar="تدريب",
            name_en="Training",
        ),
    }

    parent = _create_task_with_state(
        actor=executive,
        code="DEMO-EPIC",
        name_ar="إطلاق بوابة الخدمات",
        name_en="Launch the services portal",
        project=project,
        course=None,
        parent=None,
        assignees=[employee, contractor],
        primary=employee,
        priority=Task.Priority.HIGH,
        start_date=today - timedelta(days=30),
        due_date=today + timedelta(days=45),
        final_status=Task.Status.IN_PROGRESS,
        tags=[tags["quality"]],
    )
    _create_task_with_state(
        actor=executive,
        code="DEMO-EPIC-UX",
        name_ar="اعتماد تصميم الواجهة العربية",
        name_en="Approve the Arabic interface design",
        project=project,
        course=None,
        parent=parent,
        assignees=[contractor],
        primary=contractor,
        priority=Task.Priority.HIGH,
        start_date=today - timedelta(days=25),
        due_date=today - timedelta(days=5),
        final_status=Task.Status.COMPLETED,
        tags=[tags["quality"]],
    )
    _create_task_with_state(
        actor=executive,
        code="DEMO-EPIC-API",
        name_ar="ربط الخدمات الداخلية",
        name_en="Integrate internal services",
        project=project,
        course=None,
        parent=parent,
        assignees=[employee],
        primary=employee,
        priority=Task.Priority.HIGH,
        start_date=today - timedelta(days=20),
        due_date=today + timedelta(days=20),
        final_status=Task.Status.IN_PROGRESS,
        tags=[tags["quality"]],
    )
    blocked = _create_task_with_state(
        actor=executive,
        code="DEMO-BLOCKED",
        name_ar="حل تعطل تكامل نظام القبول",
        name_en="Resolve admissions integration blocker",
        project=project,
        course=None,
        parent=None,
        assignees=[employee],
        primary=employee,
        priority=Task.Priority.CRITICAL,
        start_date=today - timedelta(days=18),
        due_date=today - timedelta(days=2),
        final_status=Task.Status.BLOCKED,
        tags=[tags["urgent"]],
        blocking_reason="بانتظار اعتماد بيانات الربط من الجهة المالكة.",
    )
    due_soon = _create_task_with_state(
        actor=executive,
        code="DEMO-CRITICAL",
        name_ar="اختبار رحلة الطالب قبل الإطلاق",
        name_en="Test the student journey before launch",
        project=project,
        course=None,
        parent=None,
        assignees=[contractor],
        primary=contractor,
        priority=Task.Priority.CRITICAL,
        start_date=today - timedelta(days=3),
        due_date=today + timedelta(days=1),
        final_status=Task.Status.IN_PROGRESS,
        tags=[tags["urgent"], tags["quality"]],
    )
    _create_task_with_state(
        actor=executive,
        code="DEMO-TODO",
        name_ar="تجهيز خطة التواصل مع المستخدمين",
        name_en="Prepare the user communication plan",
        project=project,
        course=None,
        parent=None,
        assignees=[employee],
        primary=employee,
        priority=Task.Priority.MEDIUM,
        start_date=today,
        due_date=today + timedelta(days=30),
        final_status=Task.Status.TODO,
        tags=[tags["quality"]],
    )
    _create_task_with_state(
        actor=executive,
        code="DEMO-CANCELLED",
        name_ar="طلب تغيير خارج النطاق",
        name_en="Out-of-scope change request",
        project=project,
        course=None,
        parent=None,
        assignees=[employee],
        primary=employee,
        priority=Task.Priority.LOW,
        start_date=today - timedelta(days=10),
        due_date=today + timedelta(days=50),
        final_status=Task.Status.CANCELLED,
        tags=[tags["quality"]],
    )
    archived_task = _create_task_with_state(
        actor=executive,
        code="DEMO-OLD-TASK",
        name_ar="تحليل قديم مؤرشف",
        name_en="Archived old analysis",
        project=project,
        course=None,
        parent=None,
        assignees=[employee],
        primary=employee,
        priority=Task.Priority.LOW,
        start_date=today - timedelta(days=20),
        due_date=today + timedelta(days=10),
        final_status=Task.Status.TODO,
        tags=[tags["quality"]],
    )
    archive_task(actor=executive, task=archived_task)
    add_task_comment(
        actor=employee,
        task=blocked,
        body=("تم توثيق سبب التعطل. @demo.pm.kau نحتاج قرارًا قبل موعد الإطلاق."),
    )
    upload_task_file(
        actor=contractor,
        task=due_soon,
        upload=_pdf_upload("demo-ux-test-evidence.pdf"),
    )

    trainer = save_trainer(
        actor=executive,
        code="TR-DEMO",
        name_ar="د. أمل الزهراني",
        name_en="Dr Amal Alzahrani",
        email="trainer.demo@example.test",
        phone="+966500000101",
        organization="جهة تدريب خيالية",
        notes="مدربة خارجية خيالية لاختبار الرابط الآمن للحضور.",
    )
    course = create_course(
        actor=executive,
        code="DEMO-ENABLE",
        project=project,
        name_ar="تمكين فريق تشغيل المنصة",
        name_en="Platform Operations Team Enablement",
        description="دورة خيالية تربط التدريب بالمهام والحضور والتقارير.",
        delivery_type=Course.DeliveryType.HYBRID,
        location="جدة / عن بُعد",
        capacity=10,
        start_at=_riyadh_datetime(today - timedelta(days=30), 9),
        end_at=_riyadh_datetime(today + timedelta(days=60), 15),
        status=Course.Status.DRAFT,
        notes="تستخدم لاختبار المدربين والمتدربين والجلسات والحضور.",
    )
    course = _set_course_status(executive, course, Course.Status.ACTIVE)
    replace_course_trainers(actor=executive, course=course, trainers=[trainer])
    upload_course_file(
        actor=executive,
        course=course,
        upload=_pdf_upload("demo-course-guide.pdf"),
    )
    _create_task_with_state(
        actor=executive,
        code="DEMO-COURSE-DONE",
        name_ar="إعداد المادة التدريبية",
        name_en="Prepare training material",
        project=None,
        course=course,
        parent=None,
        assignees=[employee],
        primary=employee,
        priority=Task.Priority.MEDIUM,
        start_date=today - timedelta(days=20),
        due_date=today - timedelta(days=5),
        final_status=Task.Status.COMPLETED,
        tags=[tags["training"]],
    )
    _create_task_with_state(
        actor=executive,
        code="DEMO-COURSE-WIP",
        name_ar="متابعة تطبيق المتدربين",
        name_en="Follow up trainee application",
        project=None,
        course=course,
        parent=None,
        assignees=[employee, contractor],
        primary=employee,
        priority=Task.Priority.HIGH,
        start_date=today - timedelta(days=5),
        due_date=today + timedelta(days=25),
        final_status=Task.Status.IN_PROGRESS,
        tags=[tags["training"], tags["quality"]],
    )

    for index, full_name in enumerate(
        ("سارة أحمد الغامدي", "عبدالله محمد الزهراني"),
        start=1,
    ):
        create_enrollment(
            actor=executive,
            course=course,
            full_name=full_name,
            phone=f"0501000{index:03d}",
            email=f"direct.trainee{index}@example.test",
        )

    csv_text = (
        "الاسم الكامل,رقم الجوال,البريد الإلكتروني\n"
        "نورة خالد الحربي,0501000003,import.trainee3@example.test\n"
        "فيصل علي القرني,0501000004,import.trainee4@example.test\n"
    )
    confirmed_batch = preview_import(
        actor=executive,
        course=course,
        upload=SimpleUploadedFile(
            "demo-trainees-ar.csv",
            csv_text.encode("utf-8-sig"),
            content_type="text/csv",
        ),
    )
    confirm_import(actor=executive, batch=confirmed_batch)
    cancelled_batch = preview_import(
        actor=executive,
        course=course,
        upload=SimpleUploadedFile(
            "demo-cancelled-preview.csv",
            (
                "full_name,phone,email\nمتدرب معاينة,0501999999,preview@example.test\n"
            ).encode(),
            content_type="text/csv",
        ),
    )
    cancel_import(actor=executive, batch=cancelled_batch)

    sessions: list[Session] = []
    approved_session = create_sessions(
        actor=executive,
        course=course,
        trainer=trainer,
        title_ar="جلسة التدريب المعتمدة",
        title_en="Approved training session",
        start_at=_riyadh_datetime(today - timedelta(days=3), 10),
        end_at=_riyadh_datetime(today - timedelta(days=3), 12),
        notes="جلسة خيالية لاختبار الاعتماد والتصحيح.",
    )[0]
    sessions.append(approved_session)
    approved_link, _approved_token = issue_trainer_link(
        actor=executive,
        session=approved_session,
        lifetime_hours=24,
    )
    approved_entries: dict[int, tuple[str, str]] = {
        participant.pk: (
            str(
                AttendanceEntry.Value.LATE
                if index == 0
                else AttendanceEntry.Value.PRESENT
            ),
            "ملاحظة حضور خيالية",
        )
        for index, participant in enumerate(
            approved_session.participants.order_by("pk")
        )
    }
    approved_submission = submit_attendance(
        link=approved_link,
        entries=approved_entries,
        trainer_notes="تم إرسال الحضور للمراجعة.",
        evidence_files=[_pdf_upload("demo-attendance-evidence.pdf")],
    )
    approved_submission = review_attendance(
        actor=supervisor,
        submission=approved_submission,
        decision=AttendanceReview.Decision.APPROVED,
    )
    corrected_entries: dict[int, tuple[str, str]] = {
        entry.participant_id: (
            str(AttendanceEntry.Value.PRESENT if index == 0 else entry.value),
            "تصحيح خيالي معتمد" if index == 0 else entry.notes,
        )
        for index, entry in enumerate(
            approved_submission.entries.order_by("participant_id")
        )
    }
    correct_attendance(
        actor=executive,
        submission=approved_submission,
        entries=corrected_entries,
        reason="تصحيح أول سجل لإظهار سجل قبل وبعد.",
    )

    pending_session = create_sessions(
        actor=executive,
        course=course,
        trainer=trainer,
        title_ar="جلسة بانتظار مراجعة المشرف",
        title_en="Session awaiting supervisor review",
        start_at=_riyadh_datetime(today - timedelta(days=1), 10),
        end_at=_riyadh_datetime(today - timedelta(days=1), 12),
        notes="جلسة خيالية لاختبار الرفض وإعادة الفتح.",
    )[0]
    sessions.append(pending_session)
    pending_link, _pending_token = issue_trainer_link(
        actor=executive,
        session=pending_session,
        lifetime_hours=24,
    )
    pending_entries: dict[int, tuple[str, str]] = {
        participant.pk: (str(AttendanceEntry.Value.PRESENT), "إدخال أولي")
        for participant in pending_session.participants.order_by("pk")
    }
    pending_submission = submit_attendance(
        link=pending_link,
        entries=pending_entries,
        trainer_notes="الإرسال الأول.",
        evidence_files=[],
    )
    rejected_submission = review_attendance(
        actor=supervisor,
        submission=pending_submission,
        decision=AttendanceReview.Decision.REJECTED,
        reason="يرجى توضيح حالة الحضور قبل الاعتماد.",
    )
    resubmission_entries = {
        entry.participant_id: (entry.value, "تم التوضيح بعد الرفض")
        for entry in rejected_submission.entries.order_by("participant_id")
    }
    submit_attendance(
        link=rejected_submission.trainer_link,
        entries=resubmission_entries,
        trainer_notes="أعيد الإرسال بعد معالجة سبب الرفض.",
        evidence_files=[],
    )
    sessions.extend(
        create_sessions(
            actor=executive,
            course=course,
            trainer=trainer,
            title_ar="جلسات المتابعة الأسبوعية",
            title_en="Weekly follow-up sessions",
            start_at=_riyadh_datetime(today + timedelta(days=7), 10),
            end_at=_riyadh_datetime(today + timedelta(days=7), 11),
            recurrence=Session.Recurrence.WEEKLY,
            recurrence_count=2,
        )
    )

    milestone_outcomes = (
        ("DEMO-GATE-OK", "بوابة معتمدة", "Approved gate", "approved"),
        ("DEMO-GATE-NO", "بوابة مرفوضة", "Rejected gate", "rejected"),
        (
            "DEMO-GATE-WAIT",
            "بوابة بانتظار مدير المشروع",
            "Gate awaiting project manager",
            "pending_manager",
        ),
    )
    for code, name_ar, name_en, outcome in milestone_outcomes:
        milestone = create_milestone(
            actor=executive,
            code=code,
            project=project,
            name_ar=name_ar,
            name_en=name_en,
            description="مرحلة خيالية لإظهار حالات مسار الاعتماد المتسلسل.",
            start_date=today - timedelta(days=10),
            due_date=today + timedelta(days=10),
            status=Milestone.Status.DRAFT,
        )
        milestone = update_milestone(
            actor=executive,
            milestone=milestone,
            code=milestone.code,
            project=milestone.project,
            name_ar=milestone.name_ar,
            name_en=milestone.name_en,
            description=milestone.description,
            start_date=milestone.start_date,
            due_date=milestone.due_date,
            status=Milestone.Status.IN_PROGRESS,
        )
        approval = submit_completion(actor=executive, target=milestone)
        if outcome == "rejected":
            reject_request(
                actor=supervisor,
                approval_request=approval,
                reason="يجب استكمال دليل الاختبار قبل الاعتماد.",
            )
            continue
        approval = approve_request(actor=supervisor, approval_request=approval)
        if outcome == "approved":
            approve_request(actor=manager, approval_request=approval)

    save_filter(
        owner=ceo,
        name="المهام الحرجة والمتأخرة",
        view_type=SavedFilter.ViewType.KANBAN,
        criteria={"q": "تعطل"},
    )
    save_filter(
        owner=executive,
        name="خطة الستين يومًا القادمة",
        view_type=SavedFilter.ViewType.GANTT,
        criteria={
            "date_from": today.isoformat(),
            "date_to": (today + timedelta(days=60)).isoformat(),
        },
    )
    save_filter(
        owner=employee,
        name="مهامي الحالية",
        view_type=SavedFilter.ViewType.SEARCH,
        criteria={"q": "الخدمات"},
    )
    generate_task_deadline_notifications(today=today)

    from apps.notifications.models import Notification
    from apps.trainees.models import Trainee

    return ShowcaseSummary(
        users=User.objects.count(),
        projects=Project.objects.count(),
        courses=Course.objects.count(),
        tasks=Task.objects.count(),
        milestones=Milestone.objects.count(),
        trainees=Trainee.objects.count(),
        sessions=Session.objects.count(),
        notifications=Notification.objects.count(),
    )
