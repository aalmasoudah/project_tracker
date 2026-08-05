# Phase 17 Verification

Date: 2026-08-04

Status: Completed and verified locally

## Delivered Scope

- A permission-scoped project recovery agent with predefined goals, bounded
  optional context, an eight-step ceiling, token/time/request budgets, and a
  deterministic fake provider for offline tests.
- Dynamic use of the seven approved read tools, with permission and object
  scope rechecked before each read and after every provider response.
- Reviewed project memory that accepts only explicitly reviewed, completed
  runs and is available only to later authorized runs on the same project.
- Five strictly validated proposal types. Model output never writes business
  data and every proposal pauses in `awaiting_approval` for a human decision.
- Transactional, idempotent execution through existing task and notification
  domain services, including fresh authorization, before-state fingerprint,
  lifecycle, expiry, and duplicate-delivery checks.
- A cited verification step that reads the post-action state and records a
  bounded final summary without prompts, chain-of-thought, provider payloads,
  credentials, or raw provider errors.
- Arabic RTL/mobile and English LTR pages for starting a run, following its
  HTMX timeline, inspecting citations and before/proposed values, deciding a
  proposal, reviewing memory, and reading final verification.
- An inactive, credential-free n8n reviewed-event workflow with signed claim
  and callback operations, one-use nonces, idempotency, a human checkpoint,
  safe notification/archive handling, and execution-data retention disabled.
- A separate bilingual repository skill at
  `skills/insight-project-agent/SKILL.md` for operating and evaluating the
  agent without exposing credentials or bypassing approvals.

## Acceptance Evidence

1. Completed: a predefined goal creates a bounded stored plan before any tool
   call.
2. Completed: a successful run dynamically chooses at least two different
   allowlisted read tools; the stored calls prove the selected tools and args.
3. Completed: a dedicated provider test changes the next selected tool from
   the first observation, and the run stores both the observation and changed
   choice.
4. Completed: only an explicitly reviewed completed run creates memory; a
   later same-project run recalls and cites it while unreviewed/cross-project
   records remain unavailable.
5. Completed: every action becomes a pending proposal and the run pauses in
   `awaiting_approval` without changing the target.
6. Completed: an approved action executes once only after current permission,
   scope, proposal expiry, lifecycle, and before-state checks. Duplicate jobs
   return the existing result; stale or revoked requests make no write.
7. Completed: successful execution stores a cited final verification summary
   from the actual post-action state.
8. Completed: Arabic RTL/mobile and English LTR rendering, controls, mixed
   direction identifiers, citations, and translated validation are covered by
   the localization and Chrome suites.
9. Completed: malicious instructions, unavailable tools, forged IDs,
   unauthorized and revoked access, stale/expired proposals, request/token/
   step limits, malformed provider data, provider retries, HMAC replay, and
   duplicate execution all fail closed with bounded audit evidence.

## Migrations Reviewed

- `0001_initial.py`: protected run, step, tool-call, proposal, memory,
  reviewed-event, and integration-nonce tables with their indexes and initial
  lifecycle constraints.
- `0002_seed_phase17_permissions.py`: Phase 17 role-permission seed.
- `0003_remove_agentproposal_project_agents_proposal_decision_valid_and_more.py`:
  explicit proposal expiry state and decision constraint.
- `0004_agentintegrationnonce_expiry.py`: bounded expiry for temporary HMAC
  replay-protection records using a safe staged backfill.
- `0005_agentproposal_project_agents_proposal_action_valid_and_more.py`:
  database constraints for run, step, tool, proposal, and reviewed-event
  stable codes and lifecycle values.

The local PostgreSQL database reports all five migrations applied.
`python manage.py makemigrations --check --dry-run` reported `No changes
detected`.

## Automated Verification

- `ruff format --check .`: 352 files already formatted.
- `ruff check .`: passed.
- `mypy .`: passed across 281 source files.
- `python scripts/update_messages.py`: 1,173 Arabic messages and zero
  untranslated entries.
- `python scripts/compile_messages.py`: Arabic catalog compiled.
- `pytest -m "not browser" -q`: 200 passed, 16 deselected.
- `pytest -m browser -q`: 16 passed, 200 deselected using installed Google
  Chrome.
- `python manage.py check`: no issues.
- `python manage.py makemigrations --check --dry-run`: no changes.
- `git diff --check`: passed; reported only expected Git line-ending notices.
- The repository skill validator reported `Skill is valid!`.
- The inactive n8n JSON parsed successfully with nine nodes; tests cover
  HMAC, timestamp, nonce replay, claim lease, callback, retention settings,
  inactivity, and the absence of credential values.

## Browser and Security Verification

- The Phase 17 Chrome workflow exercised the Arabic 390 x 844 mobile flow:
  project entry point, recovery request, seven-step pre-decision timeline,
  cited proposal, human approval, execution, eighth verification step, final
  cited state, and reviewed-memory action.
- The complete 16-workflow browser suite also protected all prior critical
  Arabic/English application flows from regression.
- All database strings and optional context are treated as untrusted prompt
  data. Provider output is accepted only through strict schemas and exact
  allowlists; no shell, SQL, filesystem, arbitrary HTTP, web search, code,
  credential, file, trainee, attendance, or raw-audit tool exists.
- Provider retry, duplicate worker delivery, cancellation, stale-run recovery,
  approval concurrency, execution idempotency, and access revocation were
  verified without partial writes or leaked provider details.

## Deployment Limitation and Required Activation

A live Groq/n8n transmission was not performed because no real provider key,
HMAC secret, public HTTPS staging endpoint, or n8n credential was placed in
the repository. This is intentional: Phase 17 remains disabled by default.
Follow `docs/RUNBOOKS/PHASE_17_PROJECT_AGENT.md` to enable the fake provider
locally, then perform fictional-data security/UAT in staging before enabling
Groq or importing and activating the optional n8n workflow. The default live
model is `openai/gpt-oss-120b`; `openai/gpt-oss-20b` is available only as an
explicit lower-cost override.

Recommended commit message: `feat: add permission-scoped project recovery agent`
