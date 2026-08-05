# Decision 0021: CEO Telegram and n8n Executive Reports

Date: 2026-08-04

Status: Approved

## Decision

Phase 16 adds one narrowly authenticated n8n-to-Django integration for an
Arabic CEO Telegram bot. It is not a general public API or chatbot. The
configured active CEO and exact Telegram chat may request current-task,
overdue-task, and attendance reports. The CEO may receive trainee full names
and attendance values in the attendance PDF; no trainee contact information,
notes, files, or tokens are included.

Trainee names are not sent to Groq. AI summaries use compact aggregates, and
Django appends the authorized named rows to the final PDF. Integration calls
use HMAC-SHA256, a five-minute timestamp window, one-use nonces, bounded JSON,
and constant-time comparison. PDF download links expire in ten minutes and
are consumed once.

Critical tasks generate a protected outbox item when they are active,
non-archived, Critical priority, incomplete, and due tomorrow or earlier.
n8n leases and acknowledges alerts; failed/unacknowledged leases become
eligible for retry. One fingerprint prevents duplicate alerts for an unchanged
task status and due date.

The n8n workflow must use native credential storage for the Telegram token,
inject the signing secret from the deployment secret manager, reject every
other chat before calling Django, and disable successful and failed
execution-data retention. Django stores no Telegram bot token. Audit/log
metadata excludes chat IDs, trainee names, report content, provider payloads,
and secrets.

## Consequences

- The previously excluded third-party messaging and personal-data export
  categories now have this exact Phase 16 exception only.
- Telegram is an approved personal-data destination only for the bound CEO
  chat. Forwarding, group chats, arbitrary recipients, and other bot users are
  not approved.
- Staging uses fictional names. Production activation requires HTTPS, secret
  rotation ownership, n8n retention verification, and an end-to-end UAT.
