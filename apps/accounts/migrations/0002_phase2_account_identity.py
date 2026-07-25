# Generated and reviewed for Django 5.2.16 on 2026-07-25.

import re
import unicodedata

import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models

ARABIC_DIACRITICS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
ARABIC_SEARCH_TRANSLATION = str.maketrans(
    {
        "آ": "\u0627",
        "أ": "\u0627",
        "إ": "\u0627",
        "ٱ": "\u0627",
        "ک": "ك",
        "ی": "ي",
    }
)


def normalize_search(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value.strip()).casefold()
    normalized = ARABIC_DIACRITICS.sub("", normalized)
    normalized = normalized.replace("ـ", "")
    normalized = normalized.translate(ARABIC_SEARCH_TRANSLATION)
    return " ".join(normalized.split())


def populate_legacy_identity(apps, schema_editor) -> None:
    del schema_editor
    User = apps.get_model("accounts", "User")
    seen_usernames: dict[str, int] = {}
    seen_emails: dict[str, int] = {}

    for user in User.objects.order_by("pk").iterator():
        normalized_username = unicodedata.normalize(
            "NFKC",
            user.username.strip(),
        )
        username_key = normalized_username.casefold()
        if username_key in seen_usernames:
            conflicting_pk = seen_usernames[username_key]
            raise RuntimeError(
                "Phase 2 requires case-insensitive usernames. "
                f"Resolve accounts {conflicting_pk} and {user.pk} before migrating."
            )
        seen_usernames[username_key] = user.pk

        normalized_email = user.email.strip().casefold()
        if not normalized_email:
            normalized_email = f"phase2-legacy-{user.pk}@invalid.local"
        elif normalized_email in seen_emails:
            conflicting_pk = seen_emails[normalized_email]
            raise RuntimeError(
                "Phase 2 requires case-insensitive unique emails. "
                f"Resolve accounts {conflicting_pk} and {user.pk} before migrating."
            )
        seen_emails[normalized_email] = user.pk

        display_name = normalized_username
        search_key = normalize_search(
            f"{normalized_username} {normalized_email} {display_name}"
        )
        User.objects.filter(pk=user.pk).update(
            username=normalized_username,
            email=normalized_email,
            display_name=display_name,
            search_key=search_key,
        )


def restore_legacy_placeholder_emails(apps, schema_editor) -> None:
    del schema_editor
    User = apps.get_model("accounts", "User")
    for user in User.objects.order_by("pk").iterator():
        placeholder = f"phase2-legacy-{user.pk}@invalid.local"
        if user.email == placeholder:
            User.objects.filter(pk=user.pk).update(email="")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LoginThrottle",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "scope",
                    models.CharField(
                        choices=[("account", "Account"), ("ip", "IP address")],
                        max_length=16,
                    ),
                ),
                ("key_hash", models.CharField(max_length=64)),
                ("window_started_at", models.DateTimeField()),
                ("failure_count", models.PositiveSmallIntegerField(default=0)),
                ("locked_until", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"default_permissions": ()},
        ),
        migrations.AlterModelOptions(
            name="user",
            options={
                "permissions": (
                    ("manage_accounts", "Can administer internal accounts"),
                    (
                        "view_all_directory",
                        "Can view the complete active directory",
                    ),
                    (
                        "view_department_directory",
                        "Can view the active directory for own department",
                    ),
                    ("view_own_profile", "Can view own account profile"),
                ),
                "verbose_name": "user",
                "verbose_name_plural": "users",
            },
        ),
        migrations.AddField(
            model_name="user",
            name="deactivated_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="deactivated at",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="deactivated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="deactivated_users",
                to=settings.AUTH_USER_MODEL,
                verbose_name="deactivated by",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="users",
                to="organizations.department",
                verbose_name="department",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="display_name",
            field=models.CharField(
                default="",
                max_length=150,
                validators=[django.core.validators.MinLengthValidator(1)],
                verbose_name="display name",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="user",
            name="must_change_password",
            field=models.BooleanField(
                default=False,
                verbose_name="must change password",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="preferred_language",
            field=models.CharField(
                choices=[("ar", "Arabic"), ("en", "English")],
                default="ar",
                max_length=2,
                verbose_name="preferred language",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="search_key",
            field=models.CharField(
                db_index=True,
                default="",
                editable=False,
                max_length=500,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(max_length=254, verbose_name="email address"),
        ),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(
                error_messages={"unique": "A user with that username already exists."},
                max_length=150,
                unique=True,
                validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                verbose_name="username",
            ),
        ),
        migrations.RunPython(
            populate_legacy_identity,
            restore_legacy_placeholder_emails,
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("username"),
                name="accounts_user_username_ci_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=~models.Q(email=""),
                name="accounts_user_email_not_empty",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=~models.Q(display_name=""),
                name="accounts_user_display_name_not_empty",
            ),
        ),
        migrations.AddIndex(
            model_name="loginthrottle",
            index=models.Index(
                fields=["locked_until"],
                name="accounts_login_locked_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="loginthrottle",
            constraint=models.UniqueConstraint(
                fields=("scope", "key_hash"),
                name="accounts_login_throttle_scope_key_unique",
            ),
        ),
    ]
