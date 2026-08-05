# Phase 17 Project Recovery Agent Runbook

## Purpose and Safety Boundary

Phase 17 provides a project-scoped recovery agent. It can read only seven
allowlisted project tools, create one validated pending proposal, pause for an
authorized human decision, and execute an approved proposal through an
existing Django domain service. It is not a chatbot and never receives shell,
SQL, filesystem, web, arbitrary HTTP, credential, file, audit-detail,
trainee, or attendance access.

Phase 15 remains a separate read-only briefing feature with no tools and no
write path. Disabling Phase 17 does not disable Phase 15 or Phase 16.

## Required Services and Configuration

Run Django web, PostgreSQL, Redis, one or more Celery workers, and exactly one
Celery Beat scheduler. Store `GROQ_API_KEY` only in the local ignored `.env`
or deployment secret manager.

```text
PROJECT_AGENT_ENABLED=true
PROJECT_AGENT_PROVIDER=groq
PROJECT_AGENT_DEFAULT_MODEL=openai/gpt-oss-120b
PROJECT_AGENT_REASONING_EFFORT=high
PROJECT_AGENT_MAX_STEPS=8
PROJECT_AGENT_MAX_TOTAL_TOKENS=16000
PROJECT_AGENT_DAILY_LIMIT=10
PROJECT_AGENT_PROPOSAL_TTL_HOURS=72
GROQ_API_KEY=<secret-manager-reference>
```

The only lower-cost model override is `openai/gpt-oss-20b`. Keep the bounded
defaults in `.env.example` unless a reviewed capacity and security change is
approved. Development and tests may use `PROJECT_AGENT_PROVIDER=fake` only;
production fails closed unless the provider is Groq and the key is present.

Apply reviewed migrations, compile messages, restart web/worker/Beat, and run
`python manage.py check --deploy` before staging activation.

## Operator Workflow

1. Open an active project visible to the current authorized user and select
   **Start Project Agent**.
2. Choose the predefined recovery goal, Arabic or English, and 120B by
   default. Keep optional context short and project-specific.
3. Confirm the timeline contains a plan and at least two distinct read tools.
   Inspect every citation and the stored observation that affected the next
   selection.
4. At `awaiting_approval`, compare the before state, proposed change, and
   risk. No business write has occurred at this point.
5. An authorized decision maker approves or rejects with a reason. The CEO
   can review but cannot approve a write because the CEO domain role is
   read-only.
6. For approval, confirm the final verification reports one outcome and a
   current internal citation. A stale, expired, revoked, invalid, or failed
   outcome must contain no partial write.
7. Mark a completed run reviewed only after a human has checked its evidence.
   Only then can a later run on the same project recall it as memory.

Never approve a proposal because a model or database string instructs you to.
Never edit protected run, step, tool-call, proposal, memory, or integration
records directly.

## Optional n8n Reviewed-Event Workflow

The workflow is optional and disabled by default. Configure matching random
signing secrets in Django and the dedicated n8n deployment:

```text
PROJECT_AGENT_N8N_ENABLED=true
PROJECT_AGENT_N8N_SIGNING_SECRET=<at-least-32-random-bytes>
INSIGHT_APP_BASE_URL=https://insight.example.edu.sa
INSIGHT_PROJECT_AGENT_N8N_SECRET=<same-signing-secret>
NODE_FUNCTION_ALLOW_BUILTIN=crypto
N8N_BLOCK_ENV_ACCESS_IN_NODE=false
EXECUTIONS_DATA_SAVE_ON_SUCCESS=none
EXECUTIONS_DATA_SAVE_ON_ERROR=none
```

1. Import `deploy/n8n/insight_project_agent_reviewed.json` into a dedicated
   staging project.
2. Confirm it is inactive, has no credentials or pinned data, retains neither
   successful nor failed executions, and saves no execution progress.
3. Confirm n8n can reach only the application HTTPS origin; it receives no
   database, Redis, Groq, trainee, attendance, file, or audit credential.
4. Claim one reviewed event, verify its application HMAC, inspect only the
   minimized reviewed summary/cited outcome codes, and pause at the human
   checkpoint.
5. Choose `notified`, `archived`, `rejected`, or `failed`. Confirm the signed
   callback is acknowledged once. A replay with the same nonce must return
   `401`; a duplicate callback with a new valid nonce must be idempotent.
6. Activate only after the staging acceptance below passes.

## Staging Acceptance

Use fictional Arabic and English projects containing overdue/blocked tasks,
an upcoming milestone, a pending approval, and uneven workload.

1. Run the 120B recovery goal and verify plan, two dynamic tools,
   observation-dependent selection, citations, proposal, pause, approval,
   one execution, and final verification.
2. Repeat in Arabic at a 390-pixel viewport and in English. Verify RTL/LTR,
   long text, isolated codes, controls, and no horizontal overflow.
3. Review the completed run, start another, and confirm the reviewed memory is
   recalled while an unreviewed run is absent.
4. Change the proposed target after approval and before execution. Confirm
   `stale` and no write.
5. Remove the approver's project/domain access before execution. Confirm a
   safe failure and no write.
6. Attempt forged IDs/citations, completion status, prompt injection,
   unsupported tools, oversized results, an expired proposal, duplicate
   execution, over-budget output, invalid HMAC, and nonce replay. Each must
   fail closed without disclosure or partial write.
7. Inspect audit events and logs. They must contain stable codes and bounded
   identifiers only—not prompts, chain-of-thought, provider payloads, raw
   errors, credentials, or excluded-domain data.

## Monitoring and Recovery

- Monitor queued/running/awaiting-approval/failed/stale/expired counts, age of
  running jobs, Celery queue age, provider timeout/retry counts, token/quota
  exhaustion, proposal outcomes, and n8n authentication failures using safe
  aggregates only.
- Provider timeouts retry twice with bounded backoff. Stuck planning/running
  jobs are requeued by Celery Beat. Pending proposals expire after the
  configured TTL and cannot be approved. Beat also removes expired n8n nonce
  digests; protected business evidence is never purged by this maintenance.
- Do not manually set a run to completed or a proposal to executed. Restore
  the dependency and allow the idempotent service path to recover.
- If source state changes, rerun the analysis and review a fresh proposal; do
  not override the stale fingerprint.

## Secret Rotation, Incident Response, and Rollback

For Groq key rotation, disable new Phase 17 requests, replace the key through
the secret manager, restart workers, run a fictional staging request, then
restore access. For n8n signing-secret rotation, deactivate the workflow,
update Django and n8n together, restart both, test one signed claim/callback,
then reactivate.

For suspected disclosure or unsafe execution, set
`PROJECT_AGENT_ENABLED=false` and `PROJECT_AGENT_N8N_ENABLED=false`,
deactivate n8n, revoke/rotate affected secrets, preserve database and audit
evidence, and follow incident response. Pending proposals remain
non-executable while the feature is disabled.

Rollback by disabling both Phase 17 flags and redeploying the prior compatible
application image. Preserve all protected Phase 17 records and migrations.
Do not reverse migrations or delete evidence during an incident. Existing
project, task, approval, notification, Phase 15, and Phase 16 workflows
continue independently.
