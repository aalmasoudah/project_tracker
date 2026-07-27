"""Direction-aware course and trainer presentation helpers."""

from django import template
from django.utils.translation import get_language

from apps.courses.models import Course, Trainer

register = template.Library()


@register.filter
def localized_course_name(course: Course) -> str:
    return course.localized_name(get_language() or "ar")


@register.filter
def localized_trainer_name(trainer: Trainer) -> str:
    return trainer.localized_name(get_language() or "ar")
