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
AI_BRIEFING_MAX_OUTPUT_TOKENS=7950
AI_BRIEFING_DAILY_LIMIT=100
GROQ_RATE_LIMITER_ENABLED=true
GROQ_RATE_LIMIT_RPM=30
GROQ_RATE_LIMIT_RPD=1000
GROQ_RATE_LIMIT_TPM=8000
GROQ_RATE_LIMIT_TPD=200000
GROQ_RATE_LIMIT_TOKEN_RESERVE=256
GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS=512
GROQ_API_KEY=<secret-manager-reference>
```

The 120B/high combination prioritizes report quality. For explicitly approved
lower-cost routine use, select `openai/gpt-oss-20b`; do not silently switch
models. Input evidence is compact and bounded, output is capped, static prompt
content comes first for Groq's automatic prompt caching, and each briefing
records input, cached-input, and output token counts.

The `7950` value is a per-completion ceiling, not a fixed allocation. Before
every Groq call, the shared limiter estimates the multilingual prompt, reserves
recent organization capacity through Redis, and lowers the outgoing
`max_completion_tokens` value when required to fit the 8K TPM limit. Confirmed
cached input is excluded during reconciliation, and unused reserved tokens are
released after the response. Never set the completion ceiling equal to TPM
without adaptive prompt accounting.

Restart web/worker processes after configuration changes. Never paste the key
into source code, Django administration, task input, logs, tickets, or audit
metadata.

## Local LM Studio Development

Phase 21 permits an explicitly selected local provider in development:

```text
AI_BRIEFING_ENABLED=true
AI_BRIEFING_PROVIDER=lm_studio
AI_BRIEFING_MODEL=qwen/qwen3.5-9b
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_MODEL_CODE=qwen/qwen3.5-9b
LM_STUDIO_MODEL_ID=qwen/qwen3.5-9b
LM_STUDIO_REASONING_EFFORT=none
LM_STUDIO_API_TOKEN=
LM_STUDIO_TIMEOUT_SECONDS=180
LM_STUDIO_CONTEXT_LENGTH=32768
LM_STUDIO_CONTEXT_TOKEN_RESERVE=512
```

The logical model code is the stable allowlist/audit value; the model ID is
the exact loaded identifier returned by LM Studio and sent in the request.
They are deliberately separate. Complete the Phase 21 readiness and bilingual
strict-JSON capability probe before enabling this configuration.
The installed Qwen model passed only with `reasoning_effort=none`; the adapter
sends this setting on every local completion and rejects another Qwen value.
The gpt-oss 20B option remains supported only after explicit installation and
its own successful gate.

`LM_STUDIO_FALLBACK_ENABLED=true` does not by itself make an ordinary Phase 15
Groq briefing silently switch providers. Choose `lm_studio` explicitly for
local briefing use. Staging and production remain Groq-only. See the Phase 21
runbook for loading, readiness, security, and rollback.

## Failure and Recovery

- Temporary Groq failures and rate deferrals retry four times with bounded
  backoff or Groq's reviewed `retry-after` delay.
- Invalid schemas, forged citations, refusals, and unsafe configuration fail
  with a safe code and no partial result.
- LM Studio unavailability or invalid local output fails safely; it does not
  trigger local-to-Groq switching or tolerant JSON recovery.
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
