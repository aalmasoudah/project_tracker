"""Phase 11 notification policy and localization unit tests."""

import pytest
from django.test import override_settings
from django.utils import translation
from django.utils.translation import ngettext

from apps.accounts.models import User
from apps.notifications.emailing import render_notification_email
from apps.notifications.models import Notification
from apps.notifications.policies import (
    CATEGORY_POLICIES,
    DELIVERY_RETRY_SECONDS,
    MAX_DELIVERY_ATTEMPTS,
    MESSAGE_CATEGORIES,
    MESSAGE_CONTENT,
)


@pytest.mark.unit
def test_notification_policy_is_bilingual_bounded_and_complete() -> None:
    assert set(CATEGORY_POLICIES) == {
        "task_assignment",
        "approval",
        "deadline",
        "mention",
    }
    assert CATEGORY_POLICIES["approval"].mandatory_in_app is True
    assert MAX_DELIVERY_ATTEMPTS == 4
    assert DELIVERY_RETRY_SECONDS[:3] == (60, 300, 900)
    assert set(MESSAGE_CATEGORIES) == set(MESSAGE_CONTENT)
    assert set(MESSAGE_CATEGORIES.values()) <= set(CATEGORY_POLICIES)
    for content in MESSAGE_CONTENT.values():
        assert content.title_ar
        assert content.title_en
        assert content.body_ar
        assert content.body_en
        assert any("\u0600" <= character <= "\u06ff" for character in content.title_ar)


@pytest.mark.unit
@override_settings(APP_BASE_URL="https://tracker.example.test")
def test_email_rendering_selects_arabic_rtl_and_safe_application_link() -> None:
    recipient = User(
        username="arabic-recipient",
        email="arabic-recipient@example.test",
        display_name="مستخدم الإشعارات",
        preferred_language=User.Language.ARABIC,
    )
    notification = Notification(
        recipient=recipient,
        category=Notification.Category.TASK_ASSIGNMENT,
        message_code="task_assigned",
        event_key="unit:1",
        title_ar="إسناد مهمة جديدة",
        title_en="New task assignment",
        body_ar="تم إسناد مهمة إليك.",
        body_en="A task was assigned to you.",
        target_path="/tasks/7/",
    )

    subject, text, html = render_notification_email(notification)

    assert subject == "إسناد مهمة جديدة"
    assert "https://tracker.example.test/tasks/7/" in text
    assert 'lang="ar"' in html
    assert 'dir="rtl"' in html
    assert "فتح في النظام" in html


@pytest.mark.unit
@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, "لم يتم تحديد أي إشعار كمقروء."),
        (1, "تم تحديد إشعار واحد كمقروء."),
        (2, "تم تحديد إشعارين كمقروءين."),
        (3, "تم تحديد 3 إشعارات كمقروءة."),
        (11, "تم تحديد 11 إشعارًا كمقروء."),
        (100, "تم تحديد 100 إشعار كمقروء."),
    ],
)
def test_arabic_read_confirmation_uses_all_plural_forms(
    count: int,
    expected: str,
) -> None:
    with translation.override("ar"):
        message = ngettext(
            "Marked %(count)s notification as read.",
            "Marked %(count)s notifications as read.",
            count,
        ) % {"count": count}

    assert message == expected
