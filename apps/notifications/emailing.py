"""Localized email rendering through Django's configured backend."""

from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.notifications.models import Notification


def render_notification_email(
    notification: Notification,
) -> tuple[str, str, str]:
    language_code = (
        notification.recipient.preferred_language
        if notification.recipient.preferred_language in {"ar", "en"}
        else "ar"
    )
    title = notification.localized_title(language_code)
    body = notification.localized_body(language_code)
    target_url = (
        urljoin(
            f"{settings.APP_BASE_URL.rstrip('/')}/",
            notification.target_path.lstrip("/"),
        )
        if notification.target_path
        else settings.APP_BASE_URL
    )
    text = render_to_string(
        "notifications/email/notification.txt",
        {
            "title": title,
            "body": body,
            "target_url": target_url,
            "language_code": language_code,
        },
    )
    html = render_to_string(
        "notifications/email/notification.html",
        {
            "title": title,
            "body": body,
            "target_url": target_url,
            "language_code": language_code,
            "direction": "rtl" if language_code == "ar" else "ltr",
        },
    )
    return title, text, html


def send_notification_email(notification: Notification) -> int:
    subject, text, html = render_notification_email(notification)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[notification.recipient.email],
    )
    message.attach_alternative(html, "text/html")
    return message.send(fail_silently=False)
