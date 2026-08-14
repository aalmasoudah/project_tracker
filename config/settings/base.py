"""Settings shared by every environment."""

# Celery does not publish PEP 561 type metadata.
from celery.schedules import crontab  # type: ignore[import-untyped]
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from config.logging import build_logging_config
from config.settings.environment import BASE_DIR, env_bool, env_int, env_string

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts.apps.AccountsConfig",
    "apps.organizations.apps.OrganizationsConfig",
    "apps.audit.apps.AuditConfig",
    "apps.projects.apps.ProjectsConfig",
    "apps.courses.apps.CoursesConfig",
    "apps.tasks.apps.TasksConfig",
    "apps.approvals.apps.ApprovalsConfig",
    "apps.trainees.apps.TraineesConfig",
    "apps.attendance.apps.AttendanceConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.progress.apps.ProgressConfig",
    "apps.reports.apps.ReportsConfig",
    "apps.operations.apps.OperationsConfig",
    "apps.workspace.apps.WorkspaceConfig",
    "apps.ai_briefings.apps.AIBriefingsConfig",
    "apps.executive_bot.apps.ExecutiveBotConfig",
    "apps.project_agents.apps.ProjectAgentsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.ForcePasswordChangeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.notifications.context_processors.notification_summary",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGES = [
    ("ar", _("Arabic")),
    ("en", _("English")),
]
SUPPORTED_LANGUAGE_CODES = {code for code, _name in LANGUAGES}
LANGUAGE_CODE = env_string("DEFAULT_LANGUAGE", default="ar")
if LANGUAGE_CODE not in SUPPORTED_LANGUAGE_CODES:
    supported_languages = ", ".join(sorted(SUPPORTED_LANGUAGE_CODES))
    raise ImproperlyConfigured(
        f"DEFAULT_LANGUAGE must be one of: {supported_languages}."
    )

TIME_ZONE = env_string("TIME_ZONE", default="Asia/Riyadh")
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

LANGUAGE_COOKIE_NAME = "insight_language"
LANGUAGE_COOKIE_HTTPONLY = True
LANGUAGE_COOKIE_SAMESITE = "Lax"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/private-media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ("apps.accounts.backends.CaseInsensitiveUsernameBackend",)

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

LOGGING = build_logging_config(
    json_logs=env_bool("DJANGO_JSON_LOGS", default=True),
)

APP_BASE_URL = env_string("APP_BASE_URL", default="http://127.0.0.1:8000")
DEPLOYMENT_ENVIRONMENT = env_string(
    "DEPLOYMENT_ENVIRONMENT",
    default="development",
)
if DEPLOYMENT_ENVIRONMENT not in {"development", "test", "staging", "production"}:
    raise ImproperlyConfigured(
        "DEPLOYMENT_ENVIRONMENT must be development, test, staging, or production."
    )
DEFAULT_FROM_EMAIL = env_string("DEFAULT_FROM_EMAIL", default="tracker@example.test")
CELERY_BROKER_URL = env_string("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_BACKEND = None
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = False
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BEAT_SCHEDULE = {
    "dispatch-notification-deliveries": {
        "task": "apps.notifications.tasks.dispatch_pending_deliveries",
        "schedule": 60.0,
    },
    "generate-task-reminders": {
        "task": "apps.notifications.tasks.generate_task_reminders",
        "schedule": crontab(minute=0, hour=8),
    },
    "recover-stale-ai-briefings": {
        "task": "apps.ai_briefings.tasks.recover_stale_ai_briefings",
        "schedule": 300.0,
    },
    "maintain-executive-bot": {
        "task": "apps.executive_bot.tasks.maintain_executive_bot",
        "schedule": 300.0,
    },
    "recover-stale-project-agents": {
        "task": "apps.project_agents.tasks.recover_stale_project_agents",
        "schedule": 300.0,
    },
}

AI_BRIEFING_ENABLED = env_bool("AI_BRIEFING_ENABLED", default=False)
AI_BRIEFING_PROVIDER = env_string("AI_BRIEFING_PROVIDER", default="disabled")
AI_BRIEFING_MODEL = env_string(
    "AI_BRIEFING_MODEL",
    default="openai/gpt-oss-120b",
)
AI_BRIEFING_REASONING_EFFORT = env_string(
    "AI_BRIEFING_REASONING_EFFORT",
    default="high",
)
GROQ_API_KEY = env_string("GROQ_API_KEY")
GROQ_RATE_LIMITER_ENABLED = env_bool("GROQ_RATE_LIMITER_ENABLED", default=True)
GROQ_RATE_LIMIT_RPM = env_int("GROQ_RATE_LIMIT_RPM", default=30)
GROQ_RATE_LIMIT_RPD = env_int("GROQ_RATE_LIMIT_RPD", default=1_000)
GROQ_RATE_LIMIT_TPM = env_int("GROQ_RATE_LIMIT_TPM", default=8_000)
GROQ_RATE_LIMIT_TPD = env_int("GROQ_RATE_LIMIT_TPD", default=200_000)
GROQ_RATE_LIMIT_TOKEN_RESERVE = env_int("GROQ_RATE_LIMIT_TOKEN_RESERVE", default=256)
GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS = env_int(
    "GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS", default=512
)
GROQ_RATE_LIMIT_WINDOW_SECONDS = env_int("GROQ_RATE_LIMIT_WINDOW_SECONDS", default=60)
LM_STUDIO_BASE_URL = env_string(
    "LM_STUDIO_BASE_URL",
    default="http://127.0.0.1:1234/v1",
)
LM_STUDIO_API_TOKEN = env_string("LM_STUDIO_API_TOKEN")
LM_STUDIO_MODEL_ID = env_string(
    "LM_STUDIO_MODEL_ID",
    default="openai/gpt-oss-20b",
)
LM_STUDIO_MODEL_CODE = env_string(
    "LM_STUDIO_MODEL_CODE",
    default="openai/gpt-oss-20b",
)
LM_STUDIO_REASONING_EFFORT = env_string(
    "LM_STUDIO_REASONING_EFFORT",
    default="none",
)
LM_STUDIO_FALLBACK_ENABLED = env_bool(
    "LM_STUDIO_FALLBACK_ENABLED",
    default=False,
)
LM_STUDIO_TIMEOUT_SECONDS = env_int("LM_STUDIO_TIMEOUT_SECONDS", default=180)
LM_STUDIO_CONTEXT_LENGTH = env_int("LM_STUDIO_CONTEXT_LENGTH", default=16_384)
LM_STUDIO_CONTEXT_TOKEN_RESERVE = env_int(
    "LM_STUDIO_CONTEXT_TOKEN_RESERVE",
    default=512,
)
if LM_STUDIO_BASE_URL != "http://127.0.0.1:1234/v1":
    raise ImproperlyConfigured(
        "LM_STUDIO_BASE_URL must be the approved local loopback endpoint."
    )
AI_BRIEFING_TIMEOUT_SECONDS = env_int("AI_BRIEFING_TIMEOUT_SECONDS", default=45)
AI_BRIEFING_MAX_OUTPUT_TOKENS = env_int(
    "AI_BRIEFING_MAX_OUTPUT_TOKENS",
    default=7_950,
)
AI_BRIEFING_MAX_EVIDENCE = env_int("AI_BRIEFING_MAX_EVIDENCE", default=200)
AI_BRIEFING_DAILY_LIMIT = env_int("AI_BRIEFING_DAILY_LIMIT", default=100)
AI_BRIEFING_STALE_MINUTES = env_int("AI_BRIEFING_STALE_MINUTES", default=15)
if AI_BRIEFING_PROVIDER not in {"disabled", "fake", "groq", "lm_studio"}:
    raise ImproperlyConfigured(
        "AI_BRIEFING_PROVIDER must be disabled, fake, groq, or lm_studio."
    )
if AI_BRIEFING_REASONING_EFFORT not in {"low", "medium", "high"}:
    raise ImproperlyConfigured(
        "AI_BRIEFING_REASONING_EFFORT must be low, medium, or high."
    )
if not 1 <= AI_BRIEFING_TIMEOUT_SECONDS <= 120:
    raise ImproperlyConfigured("AI_BRIEFING_TIMEOUT_SECONDS must be between 1 and 120.")
if not 256 <= AI_BRIEFING_MAX_OUTPUT_TOKENS <= 7_950:
    raise ImproperlyConfigured(
        "AI_BRIEFING_MAX_OUTPUT_TOKENS must be between 256 and 7950."
    )
if not 1 <= GROQ_RATE_LIMIT_RPM <= 10_000:
    raise ImproperlyConfigured("GROQ_RATE_LIMIT_RPM must be between 1 and 10000.")
if not GROQ_RATE_LIMIT_RPM <= GROQ_RATE_LIMIT_RPD <= 1_000_000:
    raise ImproperlyConfigured(
        "GROQ_RATE_LIMIT_RPD must be at least RPM and at most 1000000."
    )
if not 1_000 <= GROQ_RATE_LIMIT_TPM <= 10_000_000:
    raise ImproperlyConfigured("GROQ_RATE_LIMIT_TPM must be between 1000 and 10000000.")
if not GROQ_RATE_LIMIT_TPM <= GROQ_RATE_LIMIT_TPD <= 100_000_000:
    raise ImproperlyConfigured(
        "GROQ_RATE_LIMIT_TPD must be at least TPM and at most 100000000."
    )
if not 0 <= GROQ_RATE_LIMIT_TOKEN_RESERVE < GROQ_RATE_LIMIT_TPM:
    raise ImproperlyConfigured(
        "GROQ_RATE_LIMIT_TOKEN_RESERVE must be below the TPM limit."
    )
if not 256 <= GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS <= 7_950:
    raise ImproperlyConfigured(
        "GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS must be between 256 and 7950."
    )
if not 10 <= GROQ_RATE_LIMIT_WINDOW_SECONDS <= 120:
    raise ImproperlyConfigured(
        "GROQ_RATE_LIMIT_WINDOW_SECONDS must be between 10 and 120."
    )
if LM_STUDIO_MODEL_CODE not in {
    "openai/gpt-oss-20b",
    "qwen/qwen3.5-9b",
}:
    raise ImproperlyConfigured("LM_STUDIO_MODEL_CODE must be an approved local model.")
if LM_STUDIO_REASONING_EFFORT not in {"none", "low", "medium", "high"}:
    raise ImproperlyConfigured(
        "LM_STUDIO_REASONING_EFFORT must be none, low, medium, or high."
    )
if LM_STUDIO_MODEL_CODE == "qwen/qwen3.5-9b" and LM_STUDIO_REASONING_EFFORT != "none":
    raise ImproperlyConfigured(
        "LM_STUDIO_REASONING_EFFORT must be none for qwen/qwen3.5-9b."
    )
if not LM_STUDIO_MODEL_ID or len(LM_STUDIO_MODEL_ID) > 200:
    raise ImproperlyConfigured(
        "LM_STUDIO_MODEL_ID must identify one pinned local model."
    )
if not 10 <= LM_STUDIO_TIMEOUT_SECONDS <= 600:
    raise ImproperlyConfigured("LM_STUDIO_TIMEOUT_SECONDS must be between 10 and 600.")
if not 4_096 <= LM_STUDIO_CONTEXT_LENGTH <= 131_072:
    raise ImproperlyConfigured(
        "LM_STUDIO_CONTEXT_LENGTH must be between 4096 and 131072."
    )
if not 128 <= LM_STUDIO_CONTEXT_TOKEN_RESERVE < LM_STUDIO_CONTEXT_LENGTH:
    raise ImproperlyConfigured(
        "LM_STUDIO_CONTEXT_TOKEN_RESERVE must be at least 128 and below the "
        "LM Studio context length."
    )
if not 1 <= AI_BRIEFING_MAX_EVIDENCE <= 200:
    raise ImproperlyConfigured("AI_BRIEFING_MAX_EVIDENCE must be between 1 and 200.")
if not 1 <= AI_BRIEFING_DAILY_LIMIT <= 100:
    raise ImproperlyConfigured("AI_BRIEFING_DAILY_LIMIT must be between 1 and 100.")
if not 5 <= AI_BRIEFING_STALE_MINUTES <= 120:
    raise ImproperlyConfigured("AI_BRIEFING_STALE_MINUTES must be between 5 and 120.")

EXECUTIVE_BOT_ENABLED = env_bool("EXECUTIVE_BOT_ENABLED", default=False)
EXECUTIVE_BOT_CEO_USERNAME = env_string("EXECUTIVE_BOT_CEO_USERNAME")
EXECUTIVE_BOT_TELEGRAM_CHAT_ID = env_string("EXECUTIVE_BOT_TELEGRAM_CHAT_ID")
EXECUTIVE_BOT_SIGNING_SECRET = env_string("EXECUTIVE_BOT_SIGNING_SECRET")
EXECUTIVE_BOT_SIGNATURE_TTL_SECONDS = env_int(
    "EXECUTIVE_BOT_SIGNATURE_TTL_SECONDS", default=300
)
EXECUTIVE_BOT_DOWNLOAD_TTL_SECONDS = env_int(
    "EXECUTIVE_BOT_DOWNLOAD_TTL_SECONDS", default=600
)
EXECUTIVE_BOT_MAX_BODY_BYTES = env_int("EXECUTIVE_BOT_MAX_BODY_BYTES", default=8192)
EXECUTIVE_BOT_REPORT_MAX_ROWS = env_int("EXECUTIVE_BOT_REPORT_MAX_ROWS", default=500)
EXECUTIVE_BOT_DAILY_LIMIT = env_int("EXECUTIVE_BOT_DAILY_LIMIT", default=100)
EXECUTIVE_BOT_ALERT_BATCH_SIZE = env_int("EXECUTIVE_BOT_ALERT_BATCH_SIZE", default=20)
EXECUTIVE_BOT_ALERT_LEASE_SECONDS = env_int(
    "EXECUTIVE_BOT_ALERT_LEASE_SECONDS", default=300
)
EXECUTIVE_BOT_STALE_MINUTES = env_int("EXECUTIVE_BOT_STALE_MINUTES", default=15)
EXECUTIVE_ASSISTANT_ENABLED = env_bool("EXECUTIVE_ASSISTANT_ENABLED", default=False)
EXECUTIVE_ASSISTANT_DAILY_LIMIT = env_int(
    "EXECUTIVE_ASSISTANT_DAILY_LIMIT", default=100
)
EXECUTIVE_ASSISTANT_EVIDENCE_LIMIT = env_int(
    "EXECUTIVE_ASSISTANT_EVIDENCE_LIMIT", default=40
)
EXECUTIVE_ASSISTANT_MAX_OUTPUT_TOKENS = env_int(
    "EXECUTIVE_ASSISTANT_MAX_OUTPUT_TOKENS", default=7_950
)
EXECUTIVE_ASSISTANT_STALE_MINUTES = env_int(
    "EXECUTIVE_ASSISTANT_STALE_MINUTES", default=15
)
if not 60 <= EXECUTIVE_BOT_SIGNATURE_TTL_SECONDS <= 900:
    raise ImproperlyConfigured(
        "EXECUTIVE_BOT_SIGNATURE_TTL_SECONDS must be between 60 and 900."
    )
if not 60 <= EXECUTIVE_BOT_DOWNLOAD_TTL_SECONDS <= 3_600:
    raise ImproperlyConfigured(
        "EXECUTIVE_BOT_DOWNLOAD_TTL_SECONDS must be between 60 and 3600."
    )
if not 1_024 <= EXECUTIVE_BOT_MAX_BODY_BYTES <= 65_536:
    raise ImproperlyConfigured(
        "EXECUTIVE_BOT_MAX_BODY_BYTES must be between 1024 and 65536."
    )
if not 1 <= EXECUTIVE_BOT_REPORT_MAX_ROWS <= 1_000:
    raise ImproperlyConfigured(
        "EXECUTIVE_BOT_REPORT_MAX_ROWS must be between 1 and 1000."
    )
if not 1 <= EXECUTIVE_BOT_DAILY_LIMIT <= 100:
    raise ImproperlyConfigured("EXECUTIVE_BOT_DAILY_LIMIT must be between 1 and 100.")
if not 1 <= EXECUTIVE_BOT_ALERT_BATCH_SIZE <= 50:
    raise ImproperlyConfigured(
        "EXECUTIVE_BOT_ALERT_BATCH_SIZE must be between 1 and 50."
    )
if not 60 <= EXECUTIVE_BOT_ALERT_LEASE_SECONDS <= 1_800:
    raise ImproperlyConfigured(
        "EXECUTIVE_BOT_ALERT_LEASE_SECONDS must be between 60 and 1800."
    )
if not 5 <= EXECUTIVE_BOT_STALE_MINUTES <= 120:
    raise ImproperlyConfigured("EXECUTIVE_BOT_STALE_MINUTES must be between 5 and 120.")
if not 1 <= EXECUTIVE_ASSISTANT_DAILY_LIMIT <= 100:
    raise ImproperlyConfigured(
        "EXECUTIVE_ASSISTANT_DAILY_LIMIT must be between 1 and 100."
    )
if not 5 <= EXECUTIVE_ASSISTANT_EVIDENCE_LIMIT <= 100:
    raise ImproperlyConfigured(
        "EXECUTIVE_ASSISTANT_EVIDENCE_LIMIT must be between 5 and 100."
    )
if not 256 <= EXECUTIVE_ASSISTANT_MAX_OUTPUT_TOKENS <= 7_950:
    raise ImproperlyConfigured(
        "EXECUTIVE_ASSISTANT_MAX_OUTPUT_TOKENS must be between 256 and 7950."
    )
if not 5 <= EXECUTIVE_ASSISTANT_STALE_MINUTES <= 120:
    raise ImproperlyConfigured(
        "EXECUTIVE_ASSISTANT_STALE_MINUTES must be between 5 and 120."
    )
if EXECUTIVE_ASSISTANT_ENABLED and not EXECUTIVE_BOT_ENABLED:
    raise ImproperlyConfigured(
        "EXECUTIVE_ASSISTANT_ENABLED requires EXECUTIVE_BOT_ENABLED."
    )
if EXECUTIVE_BOT_ENABLED:
    if not EXECUTIVE_BOT_CEO_USERNAME or len(EXECUTIVE_BOT_CEO_USERNAME) > 150:
        raise ImproperlyConfigured(
            "EXECUTIVE_BOT_CEO_USERNAME must identify one configured CEO."
        )
    if (
        not EXECUTIVE_BOT_TELEGRAM_CHAT_ID.isdigit()
        or int(EXECUTIVE_BOT_TELEGRAM_CHAT_ID) <= 0
    ):
        raise ImproperlyConfigured(
            "EXECUTIVE_BOT_TELEGRAM_CHAT_ID must be a positive private chat ID."
        )
    if len(EXECUTIVE_BOT_SIGNING_SECRET.encode("utf-8")) < 32:
        raise ImproperlyConfigured(
            "EXECUTIVE_BOT_SIGNING_SECRET must contain at least 32 bytes."
        )
    if not AI_BRIEFING_ENABLED or AI_BRIEFING_PROVIDER == "disabled":
        raise ImproperlyConfigured(
            "Executive Telegram reports require the approved AI provider."
        )

PROJECT_AGENT_ENABLED = env_bool("PROJECT_AGENT_ENABLED", default=False)
PROJECT_AGENT_PROVIDER = env_string("PROJECT_AGENT_PROVIDER", default="disabled")
PROJECT_AGENT_DEFAULT_MODEL = env_string(
    "PROJECT_AGENT_DEFAULT_MODEL", default="openai/gpt-oss-120b"
)
PROJECT_AGENT_REASONING_EFFORT = env_string(
    "PROJECT_AGENT_REASONING_EFFORT", default="high"
)
PROJECT_AGENT_TIMEOUT_SECONDS = env_int("PROJECT_AGENT_TIMEOUT_SECONDS", default=45)
PROJECT_AGENT_MAX_OUTPUT_TOKENS = env_int(
    "PROJECT_AGENT_MAX_OUTPUT_TOKENS", default=7_950
)
PROJECT_AGENT_MAX_TOTAL_TOKENS = env_int(
    "PROJECT_AGENT_MAX_TOTAL_TOKENS", default=50_000
)
PROJECT_AGENT_MAX_STEPS = env_int("PROJECT_AGENT_MAX_STEPS", default=8)
PROJECT_AGENT_MAX_SECONDS = env_int("PROJECT_AGENT_MAX_SECONDS", default=600)
PROJECT_AGENT_DAILY_LIMIT = env_int("PROJECT_AGENT_DAILY_LIMIT", default=100)
PROJECT_AGENT_MAX_CONTEXT_CHARS = env_int(
    "PROJECT_AGENT_MAX_CONTEXT_CHARS", default=500
)
PROJECT_AGENT_MAX_TOOL_RESULT_BYTES = env_int(
    "PROJECT_AGENT_MAX_TOOL_RESULT_BYTES", default=32_768
)
PROJECT_AGENT_MAX_TOOL_RECORDS = env_int("PROJECT_AGENT_MAX_TOOL_RECORDS", default=50)
PROJECT_AGENT_MAX_MEMORIES = env_int("PROJECT_AGENT_MAX_MEMORIES", default=5)
PROJECT_AGENT_STALE_MINUTES = env_int("PROJECT_AGENT_STALE_MINUTES", default=15)
PROJECT_AGENT_PROPOSAL_TTL_HOURS = env_int(
    "PROJECT_AGENT_PROPOSAL_TTL_HOURS", default=72
)
PROJECT_AGENT_N8N_SIGNING_SECRET = env_string("PROJECT_AGENT_N8N_SIGNING_SECRET")
PROJECT_AGENT_N8N_ENABLED = env_bool("PROJECT_AGENT_N8N_ENABLED", default=False)
PROJECT_AGENT_N8N_SIGNATURE_TTL_SECONDS = env_int(
    "PROJECT_AGENT_N8N_SIGNATURE_TTL_SECONDS", default=300
)
if PROJECT_AGENT_PROVIDER not in {"disabled", "fake", "groq", "lm_studio"}:
    raise ImproperlyConfigured(
        "PROJECT_AGENT_PROVIDER must be disabled, fake, groq, or lm_studio."
    )
if PROJECT_AGENT_DEFAULT_MODEL not in {
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
}:
    raise ImproperlyConfigured("PROJECT_AGENT_DEFAULT_MODEL is not approved.")
if PROJECT_AGENT_REASONING_EFFORT not in {"low", "medium", "high"}:
    raise ImproperlyConfigured(
        "PROJECT_AGENT_REASONING_EFFORT must be low, medium, or high."
    )
if not 1 <= PROJECT_AGENT_MAX_STEPS <= 8:
    raise ImproperlyConfigured("PROJECT_AGENT_MAX_STEPS must be between 1 and 8.")
if not 1_000 <= PROJECT_AGENT_MAX_TOTAL_TOKENS <= 50_000:
    raise ImproperlyConfigured(
        "PROJECT_AGENT_MAX_TOTAL_TOKENS must be between 1000 and 50000."
    )
if not 256 <= PROJECT_AGENT_MAX_OUTPUT_TOKENS <= 7_950:
    raise ImproperlyConfigured(
        "PROJECT_AGENT_MAX_OUTPUT_TOKENS must be between 256 and 7950."
    )
if GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS > min(
    AI_BRIEFING_MAX_OUTPUT_TOKENS,
    EXECUTIVE_ASSISTANT_MAX_OUTPUT_TOKENS,
    PROJECT_AGENT_MAX_OUTPUT_TOKENS,
):
    raise ImproperlyConfigured(
        "GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS cannot exceed an AI output ceiling."
    )
if not 10 <= PROJECT_AGENT_TIMEOUT_SECONDS <= 120:
    raise ImproperlyConfigured(
        "PROJECT_AGENT_TIMEOUT_SECONDS must be between 10 and 120."
    )
if not 30 <= PROJECT_AGENT_MAX_SECONDS <= 600:
    raise ImproperlyConfigured("PROJECT_AGENT_MAX_SECONDS must be between 30 and 600.")
if not 1 <= PROJECT_AGENT_DAILY_LIMIT <= 100:
    raise ImproperlyConfigured("PROJECT_AGENT_DAILY_LIMIT must be between 1 and 100.")
if not 100 <= PROJECT_AGENT_MAX_CONTEXT_CHARS <= 500:
    raise ImproperlyConfigured(
        "PROJECT_AGENT_MAX_CONTEXT_CHARS must be between 100 and 500."
    )
if not 4_096 <= PROJECT_AGENT_MAX_TOOL_RESULT_BYTES <= 65_536:
    raise ImproperlyConfigured(
        "PROJECT_AGENT_MAX_TOOL_RESULT_BYTES must be between 4096 and 65536."
    )
if not 1 <= PROJECT_AGENT_MAX_TOOL_RECORDS <= 100:
    raise ImproperlyConfigured(
        "PROJECT_AGENT_MAX_TOOL_RECORDS must be between 1 and 100."
    )
if not 1 <= PROJECT_AGENT_MAX_MEMORIES <= 5:
    raise ImproperlyConfigured("PROJECT_AGENT_MAX_MEMORIES must be between 1 and 5.")
if not 5 <= PROJECT_AGENT_STALE_MINUTES <= 120:
    raise ImproperlyConfigured("PROJECT_AGENT_STALE_MINUTES must be between 5 and 120.")
if not 1 <= PROJECT_AGENT_PROPOSAL_TTL_HOURS <= 168:
    raise ImproperlyConfigured(
        "PROJECT_AGENT_PROPOSAL_TTL_HOURS must be between 1 and 168."
    )
if not 60 <= PROJECT_AGENT_N8N_SIGNATURE_TTL_SECONDS <= 900:
    raise ImproperlyConfigured(
        "PROJECT_AGENT_N8N_SIGNATURE_TTL_SECONDS must be between 60 and 900."
    )
if PROJECT_AGENT_N8N_ENABLED and not PROJECT_AGENT_ENABLED:
    raise ImproperlyConfigured(
        "The project-agent n8n workflow requires PROJECT_AGENT_ENABLED=true."
    )
if (
    PROJECT_AGENT_N8N_ENABLED
    and len(PROJECT_AGENT_N8N_SIGNING_SECRET.encode("utf-8")) < 32
):
    raise ImproperlyConfigured(
        "PROJECT_AGENT_N8N_SIGNING_SECRET must contain at least 32 bytes."
    )
