"""Approved Phase 11 notification categories, defaults, and content."""

from dataclasses import dataclass
from typing import Final, NamedTuple


class NotificationContent(NamedTuple):
    title_ar: str
    title_en: str
    body_ar: str
    body_en: str


@dataclass(frozen=True)
class CategoryPolicy:
    mandatory_in_app: bool
    default_in_app: bool = True
    default_email: bool = True


CATEGORY_POLICIES: Final[dict[str, CategoryPolicy]] = {
    "task_assignment": CategoryPolicy(mandatory_in_app=False),
    "approval": CategoryPolicy(mandatory_in_app=True),
    "deadline": CategoryPolicy(mandatory_in_app=False),
    "mention": CategoryPolicy(mandatory_in_app=False),
    "ai_briefing": CategoryPolicy(
        mandatory_in_app=False,
        default_in_app=True,
        default_email=False,
    ),
    "project_agent": CategoryPolicy(
        mandatory_in_app=True,
        default_in_app=True,
        default_email=False,
    ),
}

MESSAGE_CONTENT: Final[dict[str, NotificationContent]] = {
    "task_assigned": NotificationContent(
        title_ar="إسناد مهمة جديدة",
        title_en="New task assignment",
        body_ar="تم إسناد مهمة إليك. افتح النظام لعرض التفاصيل.",
        body_en="A task was assigned to you. Open the system to view details.",
    ),
    "approval_action": NotificationContent(
        title_ar="طلب موافقة بانتظار قرارك",
        title_en="Approval awaiting your decision",
        body_ar="يوجد طلب موافقة جديد بانتظار قرارك.",
        body_en="A new approval request is waiting for your decision.",
    ),
    "approval_updated": NotificationContent(
        title_ar="تحديث على طلب موافقة",
        title_en="Approval request updated",
        body_ar="تم تحديث طلب موافقة مرتبط بعملك.",
        body_en="An approval request related to your work was updated.",
    ),
    "task_due": NotificationContent(
        title_ar="مهمة مستحقة غدًا",
        title_en="Task due tomorrow",
        body_ar="لديك مهمة مسندة يحين موعدها غدًا.",
        body_en="You have an assigned task due tomorrow.",
    ),
    "task_overdue": NotificationContent(
        title_ar="مهمة متأخرة",
        title_en="Overdue task",
        body_ar="لديك مهمة مسندة تجاوزت موعدها.",
        body_en="You have an assigned task that is overdue.",
    ),
    "mentioned": NotificationContent(
        title_ar="تمت الإشارة إليك",
        title_en="You were mentioned",
        body_ar="تمت الإشارة إليك في تعليق على مهمة يمكنك الوصول إليها.",
        body_en="You were mentioned in a comment on a task you can access.",
    ),
    "ai_briefing_ready": NotificationContent(
        title_ar="اكتمل موجز المشروع الذكي",
        title_en="AI project briefing ready",
        body_ar="اكتمل إنشاء موجز المشروع الذكي وأصبح جاهزًا للمراجعة.",
        body_en="Your AI project briefing is ready for review.",
    ),
    "agent_recovery_follow_up": NotificationContent(
        title_ar="متابعة خطة تعافي المشروع",
        title_en="Project recovery follow-up",
        body_ar=(
            "يوجد إجراء متابعة معتمد لخطة تعافي مشروع يمكنك الوصول إليه داخل النظام."
        ),
        body_en="An approved project-recovery follow-up is available in the system.",
    ),
}

MESSAGE_CATEGORIES: Final[dict[str, str]] = {
    "task_assigned": "task_assignment",
    "approval_action": "approval",
    "approval_updated": "approval",
    "task_due": "deadline",
    "task_overdue": "deadline",
    "mentioned": "mention",
    "ai_briefing_ready": "ai_briefing",
    "agent_recovery_follow_up": "project_agent",
}

MAX_DELIVERY_ATTEMPTS: Final = 4
MAX_MENTIONS_PER_COMMENT: Final = 20
DELIVERY_RETRY_SECONDS: Final[tuple[int, ...]] = (60, 300, 900, 3600)
