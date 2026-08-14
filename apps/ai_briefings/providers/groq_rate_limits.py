"""Shared adaptive Groq request budgeting for all live AI features.

The configured completion value is a ceiling, not a promise. Each request receives
the largest safe completion allowance that fits beside its estimated prompt and the
organization's recent Groq usage. Redis coordinates Celery workers; a process-local
fallback preserves safe behavior during development and isolated unit tests.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import Message
from typing import Any, Protocol, cast
from uuid import uuid4

from django.conf import settings
from redis import Redis
from redis.exceptions import LockError, RedisError


class GroqCapacityUnavailable(RuntimeError):
    """Raised before a provider call when bounded capacity will soon recover."""

    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__("Groq rate capacity is temporarily reserved.")
        self.retry_after_seconds = max(1, retry_after_seconds)


class GroqPromptBudgetExceeded(RuntimeError):
    """Raised when one prompt cannot fit beside the minimum structured output."""


@dataclass(frozen=True, slots=True)
class _Limits:
    requests_per_minute: int
    requests_per_day: int
    tokens_per_minute: int
    tokens_per_day: int
    token_reserve: int
    minimum_output_tokens: int
    window_seconds: int


@dataclass(frozen=True, slots=True)
class _BackendReservation:
    identity: str
    member: str
    day: str
    reserved_tokens: int


class _RateBackend(Protocol):
    def reserve(
        self,
        *,
        identity: str,
        estimated_input_tokens: int,
        configured_output_tokens: int,
        limits: _Limits,
        now: float,
    ) -> tuple[int, _BackendReservation]: ...

    def reconcile(
        self,
        reservation: _BackendReservation,
        *,
        actual_tokens: int,
        now: float,
    ) -> None: ...

    def release(self, reservation: _BackendReservation) -> None: ...


@dataclass(slots=True)
class GroqCapacityReservation:
    """One preflight reservation that is reconciled with provider usage."""

    max_output_tokens: int
    estimated_input_tokens: int
    reserved_tokens: int
    _backend: _RateBackend | None = None
    _backend_reservation: _BackendReservation | None = None
    _closed: bool = False

    def reconcile(
        self,
        *,
        input_tokens: int | None,
        cached_input_tokens: int | None,
        output_tokens: int | None,
    ) -> None:
        if self._closed:
            return
        counted_input = max(0, int(input_tokens or self.estimated_input_tokens))
        counted_input -= min(counted_input, max(0, int(cached_input_tokens or 0)))
        counted_output = max(0, int(output_tokens or 0))
        actual_tokens = max(1, counted_input + counted_output)
        if self._backend is not None and self._backend_reservation is not None:
            try:
                self._backend.reconcile(
                    self._backend_reservation,
                    actual_tokens=actual_tokens,
                    now=time.time(),
                )
            except (RedisError, OSError, ValueError):
                # The original worst-case reservation remains safe until expiry.
                pass
        self._closed = True

    def release(self) -> None:
        """Release a rejected request that produced no confirmed provider usage."""

        if self._closed:
            return
        if self._backend is not None and self._backend_reservation is not None:
            try:
                self._backend.release(self._backend_reservation)
            except (RedisError, OSError, ValueError):
                # Do not mask the provider outcome when quota storage is unavailable.
                pass
        self._closed = True


@dataclass(frozen=True, slots=True)
class _Usage:
    timestamp: float
    member: str
    tokens: int


@dataclass(slots=True)
class _DailyUsage:
    requests: int = 0
    tokens: int = 0


class _MemoryBackend:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._minute: dict[str, list[_Usage]] = {}
        self._daily: dict[tuple[str, str], _DailyUsage] = {}

    def reserve(
        self,
        *,
        identity: str,
        estimated_input_tokens: int,
        configured_output_tokens: int,
        limits: _Limits,
        now: float,
    ) -> tuple[int, _BackendReservation]:
        day = _utc_day(now)
        with self._lock:
            cutoff = now - limits.window_seconds
            entries = [
                item
                for item in self._minute.get(identity, [])
                if item.timestamp > cutoff
            ]
            self._minute[identity] = entries
            daily = self._daily.setdefault((identity, day), _DailyUsage())
            output_tokens = _available_output_tokens(
                minute_requests=len(entries),
                minute_tokens=sum(item.tokens for item in entries),
                daily_requests=daily.requests,
                daily_tokens=daily.tokens,
                estimated_input_tokens=estimated_input_tokens,
                configured_output_tokens=configured_output_tokens,
                limits=limits,
                now=now,
                earliest_timestamp=entries[0].timestamp if entries else None,
            )
            reserved_tokens = estimated_input_tokens + output_tokens
            member = uuid4().hex
            entries.append(_Usage(timestamp=now, member=member, tokens=reserved_tokens))
            daily.requests += 1
            daily.tokens += reserved_tokens
            reservation = _BackendReservation(
                identity=identity,
                member=member,
                day=day,
                reserved_tokens=reserved_tokens,
            )
            return output_tokens, reservation

    def reconcile(
        self,
        reservation: _BackendReservation,
        *,
        actual_tokens: int,
        now: float,
    ) -> None:
        del now
        with self._lock:
            entries = self._minute.get(reservation.identity, [])
            self._minute[reservation.identity] = [
                _Usage(item.timestamp, item.member, actual_tokens)
                if item.member == reservation.member
                else item
                for item in entries
            ]
            daily = self._daily.get((reservation.identity, reservation.day))
            if daily is not None:
                daily.tokens = max(
                    0,
                    daily.tokens - reservation.reserved_tokens + actual_tokens,
                )

    def release(self, reservation: _BackendReservation) -> None:
        with self._lock:
            entries = self._minute.get(reservation.identity, [])
            self._minute[reservation.identity] = [
                item for item in entries if item.member != reservation.member
            ]
            daily = self._daily.get((reservation.identity, reservation.day))
            if daily is not None:
                daily.requests = max(0, daily.requests - 1)
                daily.tokens = max(0, daily.tokens - reservation.reserved_tokens)


class _RedisBackend:
    def __init__(self, client: Any) -> None:
        # redis-py exposes a sync/async union in its public type surface.
        self._client = client

    @staticmethod
    def _keys(identity: str, day: str) -> tuple[str, str, str, str]:
        prefix = f"insight:groq-rate:{identity}"
        return (
            f"{prefix}:minute",
            f"{prefix}:day:{day}:requests",
            f"{prefix}:day:{day}:tokens",
            f"{prefix}:lock",
        )

    def reserve(
        self,
        *,
        identity: str,
        estimated_input_tokens: int,
        configured_output_tokens: int,
        limits: _Limits,
        now: float,
    ) -> tuple[int, _BackendReservation]:
        day = _utc_day(now)
        minute_key, day_requests_key, day_tokens_key, lock_key = self._keys(
            identity, day
        )
        with self._client.lock(lock_key, timeout=3, blocking_timeout=1):
            cutoff = now - limits.window_seconds
            self._client.zremrangebyscore(minute_key, "-inf", cutoff)
            raw_entries = self._client.zrange(minute_key, 0, -1, withscores=True)
            entries = [
                (_decoded_member(member), float(score)) for member, score in raw_entries
            ]
            daily_requests = int(self._client.get(day_requests_key) or 0)
            daily_tokens = int(self._client.get(day_tokens_key) or 0)
            output_tokens = _available_output_tokens(
                minute_requests=len(entries),
                minute_tokens=sum(_member_tokens(member) for member, _score in entries),
                daily_requests=daily_requests,
                daily_tokens=daily_tokens,
                estimated_input_tokens=estimated_input_tokens,
                configured_output_tokens=configured_output_tokens,
                limits=limits,
                now=now,
                earliest_timestamp=entries[0][1] if entries else None,
            )
            reserved_tokens = estimated_input_tokens + output_tokens
            member_id = uuid4().hex
            member = f"{member_id}:{reserved_tokens}"
            self._client.zadd(minute_key, {member: now})
            self._client.expire(minute_key, limits.window_seconds + 5)
            self._client.incr(day_requests_key)
            self._client.incrby(day_tokens_key, reserved_tokens)
            ttl = _seconds_until_utc_midnight(now) + 3_600
            self._client.expire(day_requests_key, ttl)
            self._client.expire(day_tokens_key, ttl)
        reservation = _BackendReservation(
            identity=identity,
            member=member,
            day=day,
            reserved_tokens=reserved_tokens,
        )
        return output_tokens, reservation

    def reconcile(
        self,
        reservation: _BackendReservation,
        *,
        actual_tokens: int,
        now: float,
    ) -> None:
        minute_key, _day_requests_key, day_tokens_key, lock_key = self._keys(
            reservation.identity, reservation.day
        )
        with self._client.lock(lock_key, timeout=3, blocking_timeout=1):
            score = self._client.zscore(minute_key, reservation.member)
            if score is not None:
                self._client.zrem(minute_key, reservation.member)
                member_id = reservation.member.rsplit(":", 1)[0]
                self._client.zadd(minute_key, {f"{member_id}:{actual_tokens}": score})
            difference = reservation.reserved_tokens - actual_tokens
            if difference:
                updated = int(self._client.incrby(day_tokens_key, -difference))
                if updated < 0:
                    self._client.set(day_tokens_key, 0)
        del now

    def release(self, reservation: _BackendReservation) -> None:
        minute_key, day_requests_key, day_tokens_key, lock_key = self._keys(
            reservation.identity, reservation.day
        )
        with self._client.lock(lock_key, timeout=3, blocking_timeout=1):
            removed = int(self._client.zrem(minute_key, reservation.member))
            if not removed:
                return
            requests = int(self._client.decr(day_requests_key))
            tokens = int(
                self._client.incrby(day_tokens_key, -reservation.reserved_tokens)
            )
            if requests < 0:
                self._client.set(day_requests_key, 0)
            if tokens < 0:
                self._client.set(day_tokens_key, 0)


_MEMORY_BACKEND = _MemoryBackend()
_REDIS_BACKEND: _RedisBackend | None = None
_REDIS_LOCK = threading.Lock()


def estimate_groq_input_tokens(body: dict[str, object]) -> int:
    """Conservatively estimate multilingual prompt and schema tokens.

    GPT-OSS uses a multilingual tokenizer. ASCII JSON is estimated at four
    characters per token; non-ASCII text is charged slightly above one token per
    character. The fixed allowance covers chat framing and estimation variance.
    """

    tokenized_fields = {
        key: value
        for key, value in body.items()
        if key in {"messages", "response_format", "reasoning_effort"}
    }
    serialized = json.dumps(
        tokenized_fields,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    ascii_count = sum(1 for character in serialized if ord(character) < 128)
    non_ascii_count = len(serialized) - ascii_count
    return max(
        1,
        math.ceil(ascii_count / 4) + math.ceil(non_ascii_count * 1.1) + 96,
    )


def reserve_groq_capacity(
    *,
    api_key: str,
    model: str,
    body: dict[str, object],
    configured_output_tokens: int,
) -> GroqCapacityReservation:
    limits = _limits_from_settings()
    estimated_input_tokens = estimate_groq_input_tokens(body)
    maximum_without_recent_usage = (
        limits.tokens_per_minute - limits.token_reserve - estimated_input_tokens
    )
    if maximum_without_recent_usage < limits.minimum_output_tokens:
        raise GroqPromptBudgetExceeded(
            "The request prompt cannot fit the configured Groq minute budget."
        )

    if not bool(settings.GROQ_RATE_LIMITER_ENABLED):
        output_tokens = min(configured_output_tokens, maximum_without_recent_usage)
        return GroqCapacityReservation(
            max_output_tokens=output_tokens,
            estimated_input_tokens=estimated_input_tokens,
            reserved_tokens=estimated_input_tokens + output_tokens,
        )

    identity = _quota_identity(api_key=api_key, model=model)
    try:
        backend = _backend()
        output_tokens, backend_reservation = backend.reserve(
            identity=identity,
            estimated_input_tokens=estimated_input_tokens,
            configured_output_tokens=configured_output_tokens,
            limits=limits,
            now=time.time(),
        )
    except LockError as error:
        raise GroqCapacityUnavailable(retry_after_seconds=1) from error
    except (RedisError, OSError, ValueError):
        backend = _MEMORY_BACKEND
        output_tokens, backend_reservation = backend.reserve(
            identity=identity,
            estimated_input_tokens=estimated_input_tokens,
            configured_output_tokens=configured_output_tokens,
            limits=limits,
            now=time.time(),
        )
    return GroqCapacityReservation(
        max_output_tokens=output_tokens,
        estimated_input_tokens=estimated_input_tokens,
        reserved_tokens=estimated_input_tokens + output_tokens,
        _backend=backend,
        _backend_reservation=backend_reservation,
    )


def retry_after_seconds(headers: Message | object | None) -> int | None:
    """Return Groq's bounded retry/reset delay without exposing response data."""

    if headers is None or not hasattr(headers, "get"):
        return None
    getter = headers.get
    for name in ("retry-after", "x-ratelimit-reset-tokens"):
        value = getter(name)
        parsed = _parse_duration(value)
        if parsed is not None:
            return max(1, min(parsed + 1, 3_600))
    return None


def _limits_from_settings() -> _Limits:
    return _Limits(
        requests_per_minute=int(settings.GROQ_RATE_LIMIT_RPM),
        requests_per_day=int(settings.GROQ_RATE_LIMIT_RPD),
        tokens_per_minute=int(settings.GROQ_RATE_LIMIT_TPM),
        tokens_per_day=int(settings.GROQ_RATE_LIMIT_TPD),
        token_reserve=int(settings.GROQ_RATE_LIMIT_TOKEN_RESERVE),
        minimum_output_tokens=int(settings.GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS),
        window_seconds=int(settings.GROQ_RATE_LIMIT_WINDOW_SECONDS),
    )


def _available_output_tokens(
    *,
    minute_requests: int,
    minute_tokens: int,
    daily_requests: int,
    daily_tokens: int,
    estimated_input_tokens: int,
    configured_output_tokens: int,
    limits: _Limits,
    now: float,
    earliest_timestamp: float | None,
) -> int:
    if daily_requests >= limits.requests_per_day:
        raise GroqCapacityUnavailable(
            retry_after_seconds=_seconds_until_utc_midnight(now)
        )
    if minute_requests >= limits.requests_per_minute:
        raise GroqCapacityUnavailable(
            retry_after_seconds=_minute_retry_seconds(
                now=now,
                earliest_timestamp=earliest_timestamp,
                window_seconds=limits.window_seconds,
            )
        )
    available_minute = (
        limits.tokens_per_minute
        - limits.token_reserve
        - minute_tokens
        - estimated_input_tokens
    )
    available_daily = limits.tokens_per_day - daily_tokens - estimated_input_tokens
    output_tokens = min(
        configured_output_tokens,
        available_minute,
        available_daily,
    )
    if output_tokens >= limits.minimum_output_tokens:
        return output_tokens
    if available_daily < limits.minimum_output_tokens:
        raise GroqCapacityUnavailable(
            retry_after_seconds=_seconds_until_utc_midnight(now)
        )
    raise GroqCapacityUnavailable(
        retry_after_seconds=_minute_retry_seconds(
            now=now,
            earliest_timestamp=earliest_timestamp,
            window_seconds=limits.window_seconds,
        )
    )


def _backend() -> _RateBackend:
    global _REDIS_BACKEND
    if _REDIS_BACKEND is not None:
        return _REDIS_BACKEND
    with _REDIS_LOCK:
        if _REDIS_BACKEND is None:
            broker_url = str(settings.CELERY_BROKER_URL)
            if not broker_url.startswith(("redis://", "rediss://")):
                return _MEMORY_BACKEND
            client = cast(
                Any,
                Redis.from_url(
                    broker_url,
                    decode_responses=True,
                    socket_connect_timeout=0.5,
                    socket_timeout=0.5,
                ),
            )
            client.ping()
            _REDIS_BACKEND = _RedisBackend(client)
    assert _REDIS_BACKEND is not None
    return _REDIS_BACKEND


def _quota_identity(*, api_key: str, model: str) -> str:
    digest = hashlib.sha256(f"{api_key}\0{model}".encode()).hexdigest()
    return digest[:24]


def _utc_day(now: float) -> str:
    return datetime.fromtimestamp(now, tz=UTC).date().isoformat()


def _seconds_until_utc_midnight(now: float) -> int:
    current = datetime.fromtimestamp(now, tz=UTC)
    tomorrow = datetime.combine(
        current.date() + timedelta(days=1),
        datetime.min.time(),
        tzinfo=UTC,
    )
    return max(1, math.ceil((tomorrow - current).total_seconds()))


def _minute_retry_seconds(
    *, now: float, earliest_timestamp: float | None, window_seconds: int
) -> int:
    if earliest_timestamp is None:
        return window_seconds
    return max(1, math.ceil(earliest_timestamp + window_seconds - now))


def _decoded_member(value: object) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _member_tokens(member: str) -> int:
    try:
        return max(0, int(member.rsplit(":", 1)[1]))
    except (IndexError, ValueError):
        return 0


def _parse_duration(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip().casefold()
    if not text:
        return None
    try:
        return max(0, math.ceil(float(text)))
    except ValueError:
        pass
    total = 0.0
    number = ""
    units = {"h": 3_600.0, "m": 60.0, "s": 1.0}
    for character in text:
        if character.isdigit() or character == ".":
            number += character
            continue
        if character in units and number:
            total += float(number) * units[character]
            number = ""
            continue
        return None
    if number or total <= 0:
        return None
    return math.ceil(total)
