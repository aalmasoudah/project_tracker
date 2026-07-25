"""PostgreSQL-backed login throttling without storing raw identifiers."""

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.accounts.models import LoginThrottle
from apps.accounts.normalization import normalize_login_identifier
from apps.audit.services import client_ip_address

WINDOW = timedelta(minutes=15)
LOCK_DURATION = timedelta(minutes=15)
ACCOUNT_FAILURE_LIMIT = 5
IP_FAILURE_LIMIT = 20


@dataclass(frozen=True)
class ThrottleKeys:
    """Hashed account and network identifiers for a login attempt."""

    account: str
    ip_address: str


@dataclass(frozen=True)
class ThrottleResult:
    """The lock state after checking or recording a failure."""

    account_locked: bool
    ip_locked: bool

    @property
    def locked(self) -> bool:
        return self.account_locked or self.ip_locked


def _key_hash(scope: str, value: str) -> str:
    return salted_hmac(
        f"accounts.login-throttle.{scope}",
        value,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


def throttle_keys(request: HttpRequest, username: str) -> ThrottleKeys:
    """Build non-reversible throttle identifiers."""
    account = normalize_login_identifier(username)
    ip_address = client_ip_address(request) or "unknown"
    return ThrottleKeys(
        account=_key_hash(LoginThrottle.Scope.ACCOUNT, account),
        ip_address=_key_hash(LoginThrottle.Scope.IP_ADDRESS, ip_address),
    )


def _active_lock(scope: str, key_hash: str) -> bool:
    now = timezone.now()
    throttle = LoginThrottle.objects.filter(
        scope=scope,
        key_hash=key_hash,
    ).first()
    if throttle is None:
        return False
    if throttle.locked_until is not None and throttle.locked_until > now:
        return True
    if throttle.window_started_at + WINDOW <= now:
        throttle.delete()
    return False


def check_login_locked(keys: ThrottleKeys) -> ThrottleResult:
    """Return the current account/IP lock state."""
    return ThrottleResult(
        account_locked=_active_lock(
            LoginThrottle.Scope.ACCOUNT,
            keys.account,
        ),
        ip_locked=_active_lock(
            LoginThrottle.Scope.IP_ADDRESS,
            keys.ip_address,
        ),
    )


@transaction.atomic
def _record_failure(scope: str, key_hash: str, limit: int) -> bool:
    now = timezone.now()
    throttle, _created = LoginThrottle.objects.get_or_create(
        scope=scope,
        key_hash=key_hash,
        defaults={"window_started_at": now},
    )
    throttle = LoginThrottle.objects.select_for_update().get(pk=throttle.pk)
    if throttle.window_started_at + WINDOW <= now:
        throttle.window_started_at = now
        throttle.failure_count = 0
        throttle.locked_until = None

    throttle.failure_count += 1
    if throttle.failure_count >= limit:
        throttle.locked_until = now + LOCK_DURATION
    throttle.save()
    return throttle.locked_until is not None and throttle.locked_until > now


def record_login_failure(keys: ThrottleKeys) -> ThrottleResult:
    """Increment both approved counters and report the resulting lock state."""
    return ThrottleResult(
        account_locked=_record_failure(
            LoginThrottle.Scope.ACCOUNT,
            keys.account,
            ACCOUNT_FAILURE_LIMIT,
        ),
        ip_locked=_record_failure(
            LoginThrottle.Scope.IP_ADDRESS,
            keys.ip_address,
            IP_FAILURE_LIMIT,
        ),
    )


def clear_login_failures(keys: ThrottleKeys) -> None:
    """Delete temporary counters after successful authentication."""
    LoginThrottle.objects.filter(
        scope=LoginThrottle.Scope.ACCOUNT,
        key_hash=keys.account,
    ).delete()
    LoginThrottle.objects.filter(
        scope=LoginThrottle.Scope.IP_ADDRESS,
        key_hash=keys.ip_address,
    ).delete()
