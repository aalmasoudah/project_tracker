"""Insight Tracker Django and Celery configuration."""

from config.celery import app as celery_app

__all__ = ("celery_app",)
