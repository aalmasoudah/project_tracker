"""Defense-in-depth policy checks for the configured CEO integration."""

import hashlib
import hmac

from django.conf import settings

from apps.accounts.models import User


def chat_id_hash(chat_id: str) -> str:
    return hashlib.sha256(chat_id.encode("utf-8")).hexdigest()


def can_use_executive_bot(actor: User, chat_id: str) -> bool:
    configured_username = str(settings.EXECUTIVE_BOT_CEO_USERNAME).strip()
    configured_chat = str(settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID).strip()
    return (
        bool(settings.EXECUTIVE_BOT_ENABLED)
        and actor.is_active
        and actor.username.casefold() == configured_username.casefold()
        and actor.groups.filter(name="ceo").exists()
        and actor.has_perm("executive_bot.request_executivereport")
        and hmac.compare_digest(
            chat_id.encode("utf-8"),
            configured_chat.encode("utf-8"),
        )
    )
