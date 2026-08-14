# Phase 21: Local LM Studio Inference and Controlled Fallback

Status: Approved for implementation on 2026-08-13.

## 1. Goal

Add an explicitly enabled, local-development-only LM Studio provider using one
exact pinned model from the approved local allowlist, and use it as a controlled
fallback for the existing Telegram AI features and Project Recovery Agent when
Groq has a transient provider failure. Preserve every existing evidence,
permission, citation, human-approval, execution, audit, and retention boundary.

## 2. Scope and Precedence

This phase changes provider transport and controlled failover only. It does not
expand the data, recipient, prompt, tool, proposal, action, or role scopes of
Phases 15, 16, 17, or 19.

Where earlier phase specifications or Decisions 0020, 0021, 0022, or 0024 say
that Groq is the only live provider, require a Groq secret, or require an HTTPS
provider endpoint, Decision 0026 supersedes only that provider-selection text
for the approved local-development LM Studio path. Every other earlier rule
continues unchanged. Deployed staging and production remain Groq-only until a
separate deployment and infrastructure decision explicitly approves local
inference there.

## 3. Included Features

- An OpenAI-compatible LM Studio provider at the fixed loopback base URL
  `http://127.0.0.1:1234/v1`.
- The approved logical local model allowlist is `qwen/qwen3.5-9b` and
  `openai/gpt-oss-20b`. Exactly one is configured and its exact LM Studio
  server identifier is pinned through environment configuration; it is never
  supplied by a user or discovered dynamically during a request. Unapproved
  logical models, artifacts, and deceptive aliases are rejected.
- The currently installed and live-gated local model is
  `qwen/qwen3.5-9b` (Q4_K_M, 32,768 loaded context, parallelism one). Its
  Arabic and English strict JSON Schema gate passed only with
  `reasoning_effort=none`, which is mandatory for this model. The supported
  `openai/gpt-oss-20b` path remains disabled until its artifact is explicitly
  installed and passes the same gate.
- Phase 15 AI Project Briefings may explicitly select LM Studio in local
  development. Optional Groq-to-local fallback is permitted when the global
  fallback switch is enabled, but Phase 15 fallback is not required for Phase
  21 acceptance.
- Phase 16 Telegram executive-report summaries and Phase 19 Telegram AI
  answers use Groq as primary and LM Studio as fallback when, and only when,
  the global fallback switch is explicitly enabled.
- Phase 17 Project Recovery Agent runs use Groq as primary and may make one
  controlled transition to LM Studio after a transient Groq failure. After
  authorization, configuration, status, and budget rechecks, the transition is
  persisted before the first local request; the run remains pinned to that
  exact LM Studio model for all remaining provider calls, including retries.
- Strict JSON Schema constrained generation and authoritative application-side
  schema and citation validation for every LM Studio response.
- Safe provider/model usage and one-way transition metadata without prompts,
  response bodies, reasoning, secrets, or raw provider errors.
- A local capability/evaluation gate, launcher integration, and bilingual
  operator runbook.

## 4. Excluded Features

- Exposing LM Studio to the LAN, a phone, Telegram, n8n, the public internet,
  a tunnel, a reverse proxy, staging, or production.
- Cross-Origin Resource Sharing for the LM Studio API.
- LM Studio MCP, model-controlled network access, arbitrary tools, URLs,
  browsing, filesystem, shell, code execution, SQL, credentials, or direct
  database access.
- Automatic model discovery or use of a downloaded model merely because it is
  installed. One logical code and exact server ID must match the allowlist and
  pass the Phase 21 gate.
- Provider fallback for authentication, configuration, permission, security,
  prompt-injection, schema, citation, validation, stale-state, cancellation,
  quota, token-budget, or other application errors.
- Repeated provider switching, local-to-Groq switching, provider oscillation,
  or changing the model in response to model-generated text.
- Weak prompt-only requests for "valid JSON", Markdown-fence extraction,
  tolerant parsing, schema repair by dropping fields, or accepting partially
  valid output.
- New business writes, approval bypasses, provider-selected record access, or
  changes to canonical project and task calculations.
- Installing or downloading a model automatically during normal application
  startup.

## 5. Provider and Model Configuration

- All LM Studio behavior is disabled by default and fails closed.
- The global `LM_STUDIO_FALLBACK_ENABLED` setting must be explicitly true
  before a Groq request can fall back locally.
- Phase 15 may use `AI_BRIEFING_PROVIDER=lm_studio` in local development.
- `LM_STUDIO_MODEL_CODE` is one stable allowlisted and persisted logical code.
  `LM_STUDIO_MODEL_ID` is the exact capability-probed
  server identifier returned by `/v1/models` and sent in the request body; the
  two settings must never be substituted for or inferred from one another.
- `LM_STUDIO_REASONING_EFFORT` is sent on every local completion and accepts
  `none`, `low`, `medium`, or `high`. The approved live
  `qwen/qwen3.5-9b` configuration requires exactly `none`; any other value
  fails configuration rather than risking reasoning output that exhausts or
  breaks the strict JSON result.
- Telegram reporting and assistant requests, and Project Recovery Agent runs,
  retain Groq as primary when fallback is enabled.
- The LM Studio endpoint is fixed to `http://127.0.0.1:1234/v1`; arbitrary
  schemes, hosts, ports, paths, redirects, DNS names, and URL configuration are
  rejected. The HTTP exception is safe only because the connection is
  loopback-only.
- Optional bearer-token authentication may be enabled for the local endpoint.
  The token is supplied through environment configuration, never committed,
  persisted, logged, or returned to a user. Token authentication does not
  permit non-loopback binding.
- CORS and MCP are disabled. LM Studio receives no application credentials,
  database connection string, Telegram/n8n secret, Groq key, or storage key.
- Only one model is loaded for this feature. Local inference uses a dedicated
  Celery queue and an effective concurrency of one so simultaneous website,
  Telegram, and agent work queues safely instead of overloading the laptop.
- Context, evidence, time, output-token, daily-request, retry, and total agent
  budgets remain bounded. Phase 21 never raises an earlier safety ceiling.

## 6. Structured Output Contract

Every LM Studio call sends the same bounded system instructions, untrusted
evidence envelope, and strict JSON Schema required by the calling feature. The
OpenAI-compatible request uses JSON Schema response formatting with strict
validation and closed objects (`additionalProperties: false`) where supported
by the existing schema.

LM Studio's grammar compiler does not accept the application's `maxLength`
generation annotations. The transport removes only those unsupported grammar
annotations from the schema sent to the provider; it does not repair or relax
returned data. Django still enforces every original text-length bound and the
complete application schema after parsing, so an overlong value fails closed.

Constrained generation is not authoritative. Django validates the parsed JSON
again against the exact feature schema, stable codes, enum values, sizes,
record-ID allowlists, and citation allowlist. It then rechecks current user and
object access before a result is saved or returned. Unknown fields, prose
outside the JSON object, Markdown fences, malformed Unicode, unsupported IDs,
missing citations, or unsupported factual claims fail closed.

The application extracts only the final structured result. Any `reasoning`,
`reasoning_content`, analysis, hidden trace, or equivalent gpt-oss field is
discarded before validation and is never persisted, audited, logged, included
in Telegram, or returned to the browser.

## 7. Evidence and Authority Boundaries

- PostgreSQL remains the system of record. Django selectors and services use
  the ORM to assemble only evidence already approved for the calling feature.
- LM Studio has no direct database, ORM, MCP, tool registry, filesystem, or
  credential access. It receives one bounded HTTP request from Django.
- Phase 15 remains a cited, read-only briefing with no tools or writes.
- Phase 16 named attendance rows remain local to Django. The local model, like
  Groq, receives aggregate attendance evidence only; trainee names and
  individual rows are appended deterministically after AI generation.
- Phase 19 remains standalone, read-only, no-memory, and no-tools. Its local
  fallback receives the same permission-scoped evidence and exclusions as
  Groq.
- In Phase 17, the model returns only a strict allowlisted decision. Django,
  not the model or LM Studio, validates and executes an allowlisted read or
  creates a pending proposal. Human approval, current domain permission,
  before-state fingerprint, transaction, idempotency, completion-approval
  rules, and final verification remain mandatory.
- Database and user strings remain untrusted prompt data and cannot change the
  provider, model, schema, tools, recipient, scope, or fallback decision.

## 8. Controlled Fallback Rules

A fallback is eligible only for a locally classified transient Groq failure,
such as a connection timeout, network-connect failure, rate-limit response, or
provider 5xx/unavailable response. Classification uses the response status or
stable application exception code; raw provider text is never trusted to
select fallback.

Before fallback, Django rechecks that the feature, global fallback switch,
requester, configured Telegram CEO/chat where applicable, project scope, run
budget, and local provider configuration are still valid. It also confirms
that no accepted result for that provider turn was saved.

Fallback is prohibited for:

- missing/invalid credentials or provider configuration;
- disabled features or fallback configuration;
- authentication, role, permission, chat-binding, HMAC, replay, or object-scope
  failures;
- unsafe/unsupported prompts, prompt injection, forbidden-domain requests, or
  forged identifiers;
- malformed JSON, schema failure, unsupported fields, citation failure, or
  application validation failure;
- quota, step, time, evidence, token, or total-run budget exhaustion;
- cancellation, expiry, stale state, duplicate execution, or business-rule
  failure.

Existing bounded same-provider retries may continue only where an earlier
approved feature already permits them. They do not turn an ineligible error
into a fallback error.

Telegram report and assistant requests may transition from Groq to LM Studio
once. Phase 17 may transition once at any provider turn. A safe transition
record contains only the request/run identifier, source provider/model, target
provider/model, stable transient reason code, sequence, and timestamp. It
contains no question, prompt, evidence, response, raw error, chat ID, or
secret.

For a Recovery run, the approved LM Studio provider/model transition is
persisted before the first local request, after the required rechecks. Telegram
keeps the chosen local provider/model for the rest of the request. The system
never returns to Groq or selects another local model. If LM Studio is stopped,
its model is unloaded, the local request times out, or its output fails
schema/citation validation, the existing bounded failure path is used; no
oscillation or second fallback occurs.

## 9. Token and Request Accounting

- Existing per-feature output and total-run budgets remain authoritative and
  carry across the Groq-to-LM Studio transition; fallback never resets them.
- Provider-reported prompt, completion, and total usage is stored only in the
  existing safe metric fields.
- When LM Studio omits usage, the application applies a documented
  conservative estimator to the serialized input and accepted output. Missing
  usage is never counted as zero.
- Failed and retried calls consume the conservative reserved amount required
  by the existing budget policy. A fallback is rejected if the remaining
  budget cannot safely cover it.
- Metrics distinguish `groq` and `lm_studio` without storing provider payloads
  or chain-of-thought. No token metric grants extra daily or run allowance.

## 10. Capability and Evaluation Gate

The exact local model artifact, reasoning mode, and LM Studio version must pass the gate before
`lm_studio` or fallback is enabled. The gate is repeated after a model file,
quantization, model identifier, LM Studio version, schema, or prompt-version
change.

The evaluation covers every Phase 15, 16, 17, and 19 response schema and:

- strict single-object JSON in Arabic and English;
- all required properties, enums, bounds, and no unknown properties;
- valid citations and rejection of invented/unauthorized citations;
- mixed Arabic/English identifiers and preserved RTL/LTR content;
- Phase 17 sequential decisions, allowlisted tool codes, observations,
  proposals, and final cited verification;
- prompt injection inside questions, project/task names, optional context, and
  evidence strings;
- bounded output, cancellation, timeout, unload, malformed response, and
  concurrency behavior;
- comparison against deterministic expected facts and the approved Groq
  baseline for completeness, citation precision, and useful Arabic output.

All mandatory schema, authorization, citation, and security cases must pass.
Quality or latency below the documented local acceptance threshold leaves the
provider disabled; it is not compensated for by tolerant parsing or a broader
model allowlist.

## 11. Expected Files and Migrations

Expected implementation areas include:

- a small shared LM Studio OpenAI-compatible transport and strict-response
  adapter;
- Phase 15, Phase 16/19, and Phase 17 provider dispatch and task orchestration;
- fail-closed settings and environment examples;
- stable audit/failure/transition codes and bilingual safe presentation;
- the local one-click launcher and a Phase 21 operator runbook;
- unit, integration, capability, regression, and browser tests.

One reviewed Project Recovery Agent migration extends the protected
`AgentRun.model_code` constraint to the approved Qwen logical code while
retaining both approved gpt-oss codes used by Groq/local operation. Existing
request/run, step, provider/model, usage, and audit structures are otherwise
reused. Any further model or persistence change requires a separate migration
review rather than silently dropping provider evidence.

## 12. Launcher and Runbook Requirements

The bilingual local runbook must document model acquisition, exact identifier,
capability-gate execution, optional token configuration, startup, readiness,
shutdown, log locations, common safe failure codes, and rollback. It never
contains a real API key or token.

The one-click local launcher must:

1. Find the supported LM Studio CLI without modifying machine-wide settings.
2. Confirm the exact allowlisted model is installed; it must not silently
   download a multi-gigabyte model.
3. start or reuse the loopback-only server and load the model with the exact
   pinned identifier;
4. wait for a bounded readiness check against `/v1/models` without printing a
   token;
5. start the existing Django, Redis/Celery, n8n, and Telegram processes in
   their documented order;
6. fail clearly and safely when LM Studio is unavailable while preserving the
   existing non-AI application startup path.

Repeated launcher clicks must be idempotent. A shutdown procedure stops only
processes owned by the local stack and never deletes models, project data, or
retained AI evidence.

## 13. Required Tests

- Configuration rejects default-disabled use, arbitrary URLs, non-loopback
  hosts, redirects, unknown models, missing loaded model, CORS/MCP assumptions,
  and accidental deployment activation.
- The LM Studio adapter sends strict JSON Schema requests and rejects prose,
  fences, extra fields, missing fields, invalid enums, invalid Unicode,
  reasoning-only output, oversized bodies, bad citations, and unsupported IDs.
- Optional token headers are present only when configured and never appear in
  logs, audit metadata, exceptions, snapshots, or committed files.
- Telegram `/tasks`, `/overdue`, and `/attendance` summaries and standalone
  Arabic/English questions fall back on simulated Groq timeout, rate limit, and
  5xx failures without breaking fixed commands, `/help`, `/last`, alerts,
  polling, PDF generation, or idempotency.
- Telegram never falls back for bad HMAC/chat/role, unsafe question, malformed
  primary output, schema/citation failure, quota/budget exhaustion, or invalid
  configuration.
- Phase 17 can fail over during a later step, records one safe transition,
  stays pinned to LM Studio afterward, uses at least two observations, pauses
  for approval, and retains idempotent execution and cited verification.
- Phase 17 never oscillates, never falls back on forbidden errors, and fails
  safely when the local server/model is unavailable or local output is invalid.
- Authorization revoked before fallback or later in a run prevents another
  provider call and writes nothing.
- Usage and conservative estimates accumulate across retries and fallback and
  stop before the existing budget is exceeded.
- Dedicated local-provider concurrency is one; parallel requests queue,
  cancellation is honored, and retries do not create duplicate Telegram
  replies, proposals, executions, notifications, or reports.
- Arabic and English content, mixed-direction identifiers, safe localized
  failures, and responsive existing result/agent pages pass integration and
  representative browser checks.
- Ruff formatting/linting, mypy, Django checks, the full unit/integration
  suite, critical Playwright tests, secret scan, and final diff review pass.

Automated tests use a deterministic fake OpenAI-compatible server. A separate
live LM Studio capability suite is required before local enablement but is not
silently run in normal CI or allowed to download a model.

## 14. Acceptance Criteria

1. LM Studio remains disabled by default and accepts only the exact loopback
   endpoint and one logical/API model pair from `qwen/qwen3.5-9b` or
   `openai/gpt-oss-20b`, separately pinned and capability-probed through
   `/v1/models` in local development.
2. Every accepted local result was constrained by strict JSON Schema and then
   independently validated by Django, including all citations and identifiers.
3. Telegram reports and the Telegram AI assistant use Groq first and produce
   one correct, cited local result after each approved transient-failure class.
4. Telegram does not fallback on any configuration, identity, permission,
   security, input, schema, citation, or budget failure, and existing commands
   and alerts remain working.
5. A Phase 17 run can make one audited Groq-to-LM Studio transition after a
   transient failure, remains pinned locally, and completes the existing
   multi-tool, human-approval, idempotent-execution, and cited-verification
   workflow.
6. The local model has no direct database, filesystem, MCP, network-tool,
   credential, Telegram, n8n, or business-service access.
7. Provider/model/usage/transition evidence is bounded and safe; prompts, raw
   responses/errors, secrets, and model reasoning are not retained.
8. Effective local concurrency is one, fallback and retries remain within
   existing budgets, and local unavailability fails safely without provider
   oscillation or duplicate effects.
9. Arabic and English capability, security, integration, regression, and
   representative browser checks pass, followed by the repository's complete
   quality gate and recorded manual evaluation.
10. The launcher and runbook can reproducibly start and verify the approved
    local stack without exposing LM Studio beyond loopback or downloading a
    model without an explicit operator action.
11. The installed `qwen/qwen3.5-9b` artifact passes Arabic and English strict
    JSON with `LM_STUDIO_REASONING_EFFORT=none`; any other Qwen reasoning value
    fails configuration. The gpt-oss path cannot activate until installed and
    gated.

Phase 15 optional fallback is not required to satisfy criteria 3 through 5.
Explicit Phase 15 local-provider operation must nevertheless pass the same
schema, citation, language, security, and retention tests before it is enabled.

## 15. Rollback

Set `LM_STUDIO_FALLBACK_ENABLED=false`, restore Phase 15 to its prior provider,
and stop the loopback LM Studio server. In-flight runs follow their existing
bounded cancellation/failure handling; no run is silently moved back to Groq.
Preserve all protected request, run, source, proposal, verification,
transition, usage, notification, and audit evidence. Website workflows, fixed
Telegram commands, deterministic reports, and all non-AI business domains
continue independently.
