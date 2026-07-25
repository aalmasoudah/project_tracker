# ADR 0005: Deferred Celery and Redis

- Status: Accepted
- Date: 2026-07-23
- Source: Approved scope and development playbook

## Context

Email, reminders, scheduled notifications, and long-running exports benefit
from background processing, but early phases do not require worker
infrastructure.

## Decision

Introduce Celery and Redis only in Phase 11, or earlier through a separately
approved architecture change if a required background workflow appears.
Synchronous domain services must not depend on Celery before that phase.

## Consequences

- Phases 1 through 10 have fewer runtime services.
- Background jobs must be idempotent and safe to retry.
- Business events and service boundaries should permit later asynchronous
  delivery without duplicating domain logic.
- Web, worker, and scheduler processes are deployed and monitored separately
  once background processing is introduced.
