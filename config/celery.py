"""Celery application for notification delivery and scheduled reminders."""

import os

# Celery does not publish PEP 561 type metadata.
from celery import Celery  # type: ignore[import-untyped]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("insight_tracker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
