"""Settings shared by every environment."""

# Celery does not publish PEP 561 type metadata.
from celery.schedules import crontab  # type: ignore[import-untyped]
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from config.logging import build_logging_config
from config.settings.environment import BASE_DIR, env_bool, env_string

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
}
