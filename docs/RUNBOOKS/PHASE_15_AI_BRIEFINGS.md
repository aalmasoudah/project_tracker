# Phase 15 AI Project Briefing Runbook

## Safe Local Verification

Use fictional data. In the ignored `.env` set:

```text
AI_BRIEFING_ENABLED=true
AI_BRIEFING_PROVIDER=fake
```

Start PostgreSQL, Redis, Django, one Celery worker, and one Celery Beat process.
Log in as CEO, Executive Manager, an owning Project Manager, or an assigned
Supervisor. Open an active project, generate Arabic and English briefings, open
each citation, and mark one result reviewed.

## Live Groq Configuration

Store the key only in the environment or deployment secret manager:

```text
AI_BRIEFING_ENABLED=true
AI_BRIEFING_PROVIDER=groq
AI_BRIEFING_MODEL=openai/gpt-oss-120b
AI_BRIEFING_REASONING_EFFORT=high
GROQ_API_KEY=<secret-manager-reference>
```

The 120B/high combination prioritizes report quality. For explicitly approved
lower-cost routine use, select `openai/gpt-oss-20b`; do not silently switch
models. Input evidence is compact and bounded, output is capped, static prompt
content comes first for Groq's automatic prompt caching, and each briefing
records input, cached-input, and output token counts.

Restart web/worker processes after configuration changes. Never paste the key
into source code, Django administration, task input, logs, tickets, or audit
metadata.

## Failure and Recovery

- Temporary Groq failures retry twice with bounded backoff.
- Invalid schemas, forged citations, refusals, and unsafe configuration fail
  with a safe code and no partial result.
- Celery Beat checks every five minutes for processing work older than the
  configured stale threshold and requeues at most 100 jobs per run.
- If Redis or the worker is unavailable, restore the service and inspect job
  state. Do not edit briefing rows or replay completed requests manually.
- Core projects, tasks, approvals, attendance, and reports continue normally
  during every AI-provider outage.

## Secret Rotation

Create a replacement Groq key, update the secret manager, restart workers,
verify one fictional briefing, then revoke the old key. If exposure is
suspected, disable `AI_BRIEFING_ENABLED` first, revoke the key, review safe
audit/job timing, and follow the security incident procedure.

## Rollback

Set `AI_BRIEFING_ENABLED=false` and restart web/workers. Existing briefings and
source references remain protected under the retention policy. Do not reverse
or delete the Phase 15 data migrations during an incident rollback.
