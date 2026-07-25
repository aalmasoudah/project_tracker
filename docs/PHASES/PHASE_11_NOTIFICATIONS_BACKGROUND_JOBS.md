# Phase 11: Notifications and Background Jobs

Status: Draft; blocked by notification category, recipient, timing, language,
and escalation decisions.

## 1. Goal

Implement permission-safe in-app notifications first, then localized email,
Celery, Redis, and scheduled reminders with idempotent retry-safe jobs.

## 2. Included Features

- Approved in-app notification categories for assignments, approvals,
  deadlines/overdue events, mentions, and other approved domain events.
- Notification list/read state and approved preferences.
- Email service abstraction with fake development/test backend.
- Celery worker, Redis broker, scheduler, retry/deduplication records.
- Localized Arabic/English in-app/email content chosen by approved preference/
  default behavior.

## 3. Excluded Features

- SMS, chat integrations, push notifications, and unapproved categories.
- Background ownership of domain transactions.
- Email containing sensitive data beyond approved policy.
- User suppression of mandatory categories unless explicitly approved.

## 4. User Stories

- As a user, I receive permitted notifications for approved events.
- As a user, I can mark notifications read and configure only allowed
  preferences.
- As an operator, I can retry failed jobs without duplicate notification/email.
- As an Arabic-speaking recipient, I receive complete, reviewed Arabic content
  with correct RTL email rendering.

## 5. Models Involved

- `notifications.Notification`, `NotificationPreference`.
- `DeliveryAttempt`/outbox/deduplication record as selected.
- References to source event/target using an explicit safe design.

## 6. Pages Involved

- Notification list/detail or bounded target link.
- Read/unread actions and approved preference screen.
- Technical delivery status only for approved operational roles.

## 7. Permission Requirements

Recipients must be computed from approved object access at event time.
Notification existence/content/target links cannot reveal inaccessible
records. Preference and operational delivery views are owner/admin scoped.

## 8. Validation Rules

- Categories, recipients, timing, escalation, expiry, and preference controls
  come from approved policy.
- Stable deduplication keys prevent repeated event/job delivery.
- Jobs are idempotent, bounded, retry-safe, and record safe failure metadata.
- Locale selection follows approved user preference/default; missing
  translation uses an explicit safe fallback policy and is detected in tests.
- Email addresses/content/links are validated and environment-correct.

## 9. Business Rules

- Background jobs must be idempotent and safe to retry.
- Resolve `BR-14`, `BR-17`, recipient/timing/escalation rules, email-sensitive
  content, and `L10N-01`/`L10N-02`.
- Domain writes succeed independently of provider delivery while preserving a
  reliable approved event/outbox boundary.

## 10. Expected Migrations

- Initial notification, preference, and delivery/deduplication models.
- Unique constraints for deduplication and indexes for recipient, category,
  read state, schedule, and failure queues.

## 11. Unit Tests

- Recipient/category/preference policy.
- Locale/template selection and Arabic pluralization.
- Deduplication, retry, backoff, and idempotency.
- Email abstraction and safe logging.

## 12. Integration Tests

- Approved domain event creates exactly one in-app notification.
- Preference suppression/mandatory delivery.
- Worker success/failure/retry without duplicates.
- Scheduled overdue/deadline events using approved time semantics.
- Arabic/English email rendering and inaccessible target handling.

## 13. Browser Tests

- Trigger, view, mark read, and follow an authorized notification.
- Configure allowed preferences.
- Verify core notification workflow in Arabic RTL and English LTR.

## 14. Security Tests

- Cross-user notification/preferences access.
- Restricted target/title/body leakage.
- Forged notification links, unsafe external URLs, email header injection,
  secrets/personal content in logs, and replay/duplicate delivery.

## 15. Manual Verification

- Trigger assignment/approval/overdue examples.
- Run worker/scheduler with fake email and inspect retries/deduplication.
- Disable an approved category and verify behavior.
- Review Arabic/English subject, body, direction, links, and terminology.

## 16. Acceptance Criteria

- Approved events create correct, permission-safe in-app notifications.
- Preferences affect only allowed categories.
- Email is abstracted, localized, and fake in development/tests.
- Celery/Redis jobs are idempotent, retry-safe, deduplicated, and monitored.
- Arabic/English in-app and email workflows pass localization verification.
- No SMS or unrelated integration exists.

## 17. Dependencies

- Approved event-producing domain phases and ADR 0005.
- Approved categories, recipients, preferences, timing, escalation, retention,
  email content, timezone, and permissions.
- Approved user/default language and Arabic terminology.

## 18. Rollback Considerations

- A rollback must not replay delivered events or strand incompatible queued
  payloads.
- Version task payloads and drain/revoke queues through an approved procedure.
- Preserve notification/delivery audit according to retention policy.
