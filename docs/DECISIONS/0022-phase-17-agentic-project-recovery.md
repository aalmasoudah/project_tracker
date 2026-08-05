# Decision 0022: Agentic Project Recovery and Planning

Date: 2026-08-04

Status: Approved

## Decision

Phase 17 is a new `project_agents` domain and does not extend or alter the
Phase 15 read-only AI briefing loop. It may use only seven named read tools
and five named proposal tools. A model can never call a business write
service. It can only create a validated pending proposal that pauses for an
authorized human decision.

The approving user is the actor for execution. Execution requires both the
new Phase 17 permission and the existing domain permission for the exact
action and object. It runs transactionally with row locks, an idempotency key,
and a before-state fingerprint, then performs a fresh read to create a cited
verification result. Existing task-completion approvals remain mandatory;
Phase 17 rejects proposals for Completed, Cancelled, or Pending Approval task
states.

Runs use strict structured decisions, at most eight stored steps, a total
token/time budget, bounded tool results, and daily request limits. Database
text and optional user context are untrusted prompt data. The application
stores concise plans, calls, observations, proposals, and finals but never
chain-of-thought, full prompts, credentials, raw provider payloads, or raw
provider errors. The default Groq model is `openai/gpt-oss-120b`; the only
lower-cost override is `openai/gpt-oss-20b`.

The proposal decision includes cited findings and recommendations, allowing
Django to store the final report step in the same iteration instead of making
a redundant provider call over the same evidence. This reduces repeated
input tokens without weakening strict validation, citations, human approval,
or the final post-execution verification step.

Persistent memory is a reviewed, cited summary, scoped to one project. It is
created only after an authorized user explicitly reviews a completed verified
run. An unreviewed, failed, cancelled, expired, stale, or out-of-scope run can
never become memory.

The optional n8n workflow receives only a safe reviewed-event envelope through
signed HMAC endpoints, applies a human checkpoint, then sends a signed
idempotent callback. It excludes sensitive domains and stores no credential
values in its export. The repository skill is a documented course artifact,
not a runtime dependency and not an approval bypass.

## Consequences

- The initial-release prohibition on autonomous writes now has one narrow
  exception: an explicitly approved Phase 17 proposal may execute through an
  existing service under the approving user's current authority.
- CEO can analyze and review but remains unable to mutate business data
  because the existing CEO domain role is read-only.
- Provider-selected IDs, URLs, tools, and actions are not trusted. IDs must
  originate from server-issued observations and are re-resolved in current
  scope.
- Fixed project-agent notifications require a new notification category and
  bilingual message catalog entry; arbitrary provider text is never sent.
- Protected Phase 17 records follow the Phase 14 retention policy and remain
  available if the feature is disabled.
