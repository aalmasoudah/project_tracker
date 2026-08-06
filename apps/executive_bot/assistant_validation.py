"""Local fail-closed validation for standalone executive questions."""

import re
from typing import Final

from django.core.exceptions import ValidationError

MIN_QUESTION_LENGTH: Final = 3
MAX_QUESTION_LENGTH: Final = 500

ARABIC_PATTERN: Final = re.compile(r"[\u0600-\u06ff]")
CONTROL_PATTERN: Final = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
URL_PATTERN: Final = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)
CREDENTIAL_PATTERN: Final = re.compile(
    r"(?:gsk_[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]+|\d{8,}:[A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)

SUPPORTED_TERMS: Final = (
    "task",
    "tasks",
    "project",
    "projects",
    "risk",
    "risks",
    "problem",
    "problems",
    "deadline",
    "deadlines",
    "overdue",
    "late",
    "blocked",
    "blocker",
    "progress",
    "milestone",
    "approval",
    "approvals",
    "priority",
    "urgent",
    "attention",
    "workload",
    "finish",
    "finished",
    "مهمة",
    "مهام",
    "مشروع",
    "مشاريع",
    "خطر",
    "مخاطر",
    "مشكلة",
    "مشاكل",
    "موعد",
    "مواعيد",
    "متأخر",
    "متأخرة",
    "تعطل",
    "متعطل",
    "عالق",
    "تقدم",
    "إنجاز",
    "مرحلة",
    "اعتماد",
    "موافقة",
    "أولوية",
    "حرج",
    "عاجل",
    "اهتمام",
    "عبء",
    "تنتهي",
    "ينتهي",
)

BLOCKED_TERMS: Final = (
    "ignore previous",
    "ignore all",
    "system prompt",
    "developer message",
    "reveal prompt",
    "show prompt",
    "chain of thought",
    "password",
    "api key",
    "secret",
    "credential",
    "access token",
    "shell",
    "powershell",
    "command prompt",
    "raw sql",
    "select *",
    "drop table",
    "filesystem",
    "file contents",
    "web search",
    "browse the web",
    "http request",
    "trainee",
    "trainees",
    "attendance",
    "phone number",
    "email address",
    "employee name",
    "employee names",
    "تجاهل التعليمات",
    "تجاهل الأوامر",
    "تعليمات النظام",
    "أظهر البرومبت",
    "اكشف البرومبت",
    "سلسلة التفكير",
    "كلمة المرور",
    "كلمات المرور",
    "مفتاح api",
    "مفتاح الواجهة",
    "سر النظام",
    "بيانات الدخول",
    "سطر الأوامر",
    "قاعدة البيانات",
    "ملفات النظام",
    "ابحث في الويب",
    "متدرب",
    "متدربين",
    "الحضور",
    "رقم الجوال",
    "البريد الإلكتروني",
    "أسماء الموظفين",
)

WRITE_PATTERNS: Final = (
    re.compile(
        r"\b(?:create|update|delete|change|approve|reject|assign|cancel|complete)\b"
        r".{0,30}\b(?:task|project|approval|assignment|deadline)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:أنشئ|أنشء|حدث|احذف|غيّر|وافق|ارفض|أسند|ألغ|أكمل)"
        r".{0,30}(?:مهمة|مشروع|اعتماد|موافقة|موعد)",
    ),
)


def detect_question_language(question: str) -> str:
    return "ar" if ARABIC_PATTERN.search(question) else "en"


def validate_executive_question(question: object) -> tuple[str, str]:
    """Return normalized question/language or reject before any provider call."""
    if not isinstance(question, str):
        raise ValidationError("invalid_question")
    cleaned = question.strip()
    if not MIN_QUESTION_LENGTH <= len(cleaned) <= MAX_QUESTION_LENGTH:
        raise ValidationError("invalid_question")
    if cleaned.startswith("/") or CONTROL_PATTERN.search(cleaned):
        raise ValidationError("unsupported_question")
    folded = cleaned.casefold()
    if (
        URL_PATTERN.search(cleaned)
        or CREDENTIAL_PATTERN.search(cleaned)
        or any(term in folded for term in BLOCKED_TERMS)
        or any(pattern.search(cleaned) for pattern in WRITE_PATTERNS)
    ):
        raise ValidationError("unsafe_question")
    if not any(term in folded for term in SUPPORTED_TERMS):
        raise ValidationError("unsupported_question")
    return cleaned, detect_question_language(cleaned)
