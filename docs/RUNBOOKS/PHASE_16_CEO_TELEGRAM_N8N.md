# Phase 16 CEO Telegram and n8n Runbook

## Purpose and Privacy Boundary

This workflow gives one configured active CEO, in one exact private Telegram
chat, four fixed Arabic commands:

| Command | Result |
| --- | --- |
| `/help` | Arabic command help |
| `/tasks` | Current-task executive PDF |
| `/overdue` | Overdue-task executive PDF |
| `/attendance` | Attendance executive PDF for the last 30 days |

The attendance PDF contains the trainee full name and attendance status under
the owner's explicit Phase 16 approval. It does not contain phone numbers,
email addresses, attendance notes, trainer notes, comments, files, or tokens.
Groq receives attendance aggregates only and never receives trainee names or
individual attendance rows.

## Required Services

- Django web, PostgreSQL, Redis, one Celery worker, and exactly one Celery Beat
  process.
- A dedicated n8n staging/production project reachable through HTTPS.
- A Telegram bot created for Insight Projects / إنسايت بروجكتس and a private
  one-to-one chat with the approved CEO.
- Synchronized server clocks. Signed requests permit at most five minutes of
  clock skew.

Do not use a Telegram group, channel, shared account, or a personal automation
workflow for production delivery.

## Django Configuration

Inject these values from the deployment secret manager. The username must
identify exactly one active user in the `ceo` group with the seeded Phase 16
permission. The chat ID must be the positive numeric ID of the private CEO
chat.

```text
APP_BASE_URL=https://insight.example.edu.sa
AI_BRIEFING_ENABLED=true
AI_BRIEFING_PROVIDER=groq
AI_BRIEFING_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=<secret-manager-reference>
EXECUTIVE_BOT_ENABLED=true
EXECUTIVE_BOT_CEO_USERNAME=<approved-ceo-username>
EXECUTIVE_BOT_TELEGRAM_CHAT_ID=<approved-private-chat-id>
EXECUTIVE_BOT_SIGNING_SECRET=<at-least-32-random-bytes>
```

Keep the bounded defaults in `.env.example` unless a reviewed capacity change
requires different values. Apply migrations, restart web/worker/scheduler,
and run `python manage.py check --deploy` before activating n8n.

## n8n Configuration and Import

Provide these secret-manager-backed environment values to the n8n main and
task-runner processes. The signing secret must exactly match Django.

```text
INSIGHT_APP_BASE_URL=https://insight.example.edu.sa
INSIGHT_TELEGRAM_CEO_CHAT_ID=<same-approved-private-chat-id>
INSIGHT_N8N_SIGNING_SECRET=<same-signing-secret>
NODE_FUNCTION_ALLOW_BUILTIN=crypto
N8N_BLOCK_ENV_ACCESS_IN_NODE=false
EXECUTIONS_DATA_SAVE_ON_SUCCESS=none
EXECUTIONS_DATA_SAVE_ON_ERROR=none
```

The Code nodes need the built-in Node.js `crypto` module to calculate the
documented HMAC. The signed HTTP nodes must use n8n's native JSON body mode;
raw body mode returns a response stream instead of parsed JSON in the pinned
n8n version. Limit environment access to the dedicated n8n deployment and its
operators. Never paste a secret into a Code node, expression, workflow JSON,
pinned data, execution note, or ticket.

1. Create a native n8n Telegram credential containing the bot token.
2. Import `deploy/n8n/insight_ceo_telegram_reports.json`.
3. Bind that credential to the Telegram Trigger and all Telegram send nodes.
4. Confirm the imported workflow is inactive and has no pinned data.
5. Confirm workflow settings save neither successful nor failed execution
   data and do not save execution progress.
6. Verify every endpoint uses the production HTTPS application origin.
7. Run staging acceptance with fictional Arabic data, then activate the
   workflow only after the checklist below passes.

Telegram must be able to reach the n8n production webhook over valid HTTPS.
n8n must be able to reach the Django `APP_BASE_URL` over valid HTTPS. Do not
expose PostgreSQL or Redis to n8n.

## Staging Acceptance Test

Use a staging bot, staging CEO/chat, staging signing secret, and fictional
Arabic data.

1. Send `/help`; verify only the four fixed Arabic commands appear.
2. Send `/tasks`; open the branded Arabic PDF and check current task rows,
   Gregorian/Hijri dates, RTL order, filename, logo proportions, and totals.
3. Send `/overdue`; verify known overdue tasks appear and completed/cancelled
   tasks do not.
4. Send `/attendance`; verify fictional trainee names and attendance statuses
   appear, while phone, email, attendance notes, and trainer notes do not.
5. From another Telegram chat, send every command. Verify no response and no
   Django report request.
6. Reuse one captured signed request. Verify Django returns `401` and does not
   create a second report.
7. Reuse a completed PDF URL. Verify the first download succeeds and the
   second returns `404`; also verify expiry after ten minutes.
8. Create a fictional active Critical task due tomorrow. Within five minutes,
   verify one Arabic alert arrives. Temporarily break Telegram delivery,
   restore it after the lease expires, and verify retry followed by one
   acknowledgement without duplicate acknowledged alerts.
9. Inspect Django audit records, application/worker logs, n8n execution policy,
   and provider telemetry. They must not contain the chat ID, signing secret,
   bot token, trainee names, attendance rows, report body, or provider payload.

Do not perform the privacy test using real trainee data.

## Monitoring and Recovery

- Monitor report queued/processing/failed counts, Celery queue age, failed
  Groq calls, integration authentication failures, unacknowledged alert age,
  and Telegram/n8n availability using safe counts only.
- n8n polls report status every five seconds for at most ten minutes. A failed
  report returns a safe Arabic message; application business workflows remain
  available.
- Unacknowledged critical alerts become eligible after the five-minute lease.
  Do not edit outbox rows or acknowledge alerts manually.
- If clocks drift, restore NTP synchronization before retrying requests.
- If n8n is unavailable, Django continues discovering alerts and retaining the
  protected outbox. Restore n8n and allow normal claim/acknowledgement.

## Secret Rotation and Incident Response

For a planned signing-secret rotation, deactivate the workflow, update Django
and n8n from the same new secret-manager value, restart both services, run a
fictional signed request, and reactivate. Rotate the Telegram token in its
native n8n credential independently. Rotate the Groq key according to the
Phase 15 runbook.

For suspected disclosure, deactivate n8n and set
`EXECUTIVE_BOT_ENABLED=false`, revoke the Telegram token, rotate the signing
secret and Groq key as applicable, preserve audit/outbox evidence, inspect the
bound chat, and follow the security incident process. Never delete evidence to
hide an incident.

## Rollback

Deactivate the n8n workflow, set `EXECUTIVE_BOT_ENABLED=false`, and restart
Django processes. Preserve Phase 16 report, alert, nonce, and audit records.
Do not reverse migrations during an incident. Projects, tasks, attendance,
ordinary reports, and Phase 15 in-app briefings continue to operate.
