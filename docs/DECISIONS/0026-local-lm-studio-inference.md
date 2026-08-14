# Decision 0026: Local LM Studio Inference and Controlled Fallback

Date: 2026-08-13

Status: Approved

## Context

Insight Tracker currently uses Groq for approved AI project briefings,
Telegram summaries and executive questions, and Project Recovery Agent
decisions. Local development needs a private fallback when Groq is temporarily
unavailable or rate limited, without weakening structured output, evidence
scope, permissions, citations, human approval, token budgets, or retention.

Earlier Decisions 0020, 0021, 0022, and 0024 bind live inference to Groq and an
HTTPS endpoint. A loopback-only LM Studio service requires one narrow local
exception and an explicit rule for provider transitions.

## Decision

LM Studio is approved only for local development at the fixed OpenAI-compatible
base URL `http://127.0.0.1:1234/v1`. Approved logical local models are
`qwen/qwen3.5-9b` and `openai/gpt-oss-20b`, configured as
`LM_STUDIO_MODEL_CODE`; exactly one separate `LM_STUDIO_MODEL_ID` value pins
the matching capability-probed identifier returned by `/v1/models` and sent in
the request body. Neither value is user-selectable or silently inferred from
the other, and deceptive aliases are rejected. The endpoint is not configurable to
another host, is not
exposed to the LAN, phone, n8n, Telegram, tunnel, or public internet, and runs
with CORS and MCP disabled. Optional bearer-token authentication is supplied
only through environment configuration. Local-provider use and the global
`LM_STUDIO_FALLBACK_ENABLED` switch are disabled by default.

Every request uses strict JSON Schema constrained output. Django remains the
authority: it parses once, validates the complete application schema, stable
codes, bounds, record allowlist, citations, current identity, permission, and
object scope, then fails closed on any mismatch. It never accepts Markdown-
wrapped or partially repaired JSON. Any reasoning or analysis field is
discarded and is never stored, logged, audited, or delivered.

Because LM Studio's grammar compiler rejects the application's `maxLength`
generation annotations, the local transport removes only those unsupported
annotations from the provider-facing grammar. It does not modify or repair the
returned object. The unchanged Django validator remains authoritative for every
original text-length bound and rejects overlong output.

Live local evaluation on 2026-08-13 established
`qwen/qwen3.5-9b` (Q4_K_M, loaded with a 32,768-token context and parallelism
one) as the currently available local artifact. Its Arabic and English strict
JSON Schema probe passed only with `reasoning_effort=none`; Phase 21 therefore
requires `LM_STUDIO_REASONING_EFFORT=none` for this Qwen model. The setting is
sent on every local completion and accepts only `none`, `low`, `medium`, or
`high`; a conflicting Qwen value fails configuration. The
`openai/gpt-oss-20b` model remains supported but cannot activate until an
operator explicitly installs its artifact and it passes the same capability
gate. Catalog or tool-use metadata never replaces that gate.

LM Studio has no direct PostgreSQL, ORM, filesystem, MCP, shell, SQL, network
tool, credential, or business-service access. Django sends only the bounded
evidence already approved by the calling phase. Phase 16 trainee names and
individual attendance rows remain local and are not included in either Groq
or LM Studio evidence. Phase 17 local output may select only existing stable
read/proposal codes; Django retains every permission recheck, pending human
approval, stale-state fingerprint, transactional idempotent domain-service
execution, completion-approval rule, and final verification.

Phase 15 may select LM Studio explicitly in local development and may
optionally use the global fallback. Phase 15 fallback is not part of the Phase
21 acceptance gate. Phase 16 Telegram report summaries, Phase 19 Telegram AI
answers, and Phase 17 Recovery Agent runs use Groq as primary and require the
controlled fallback for Phase 21 acceptance.

Fallback is allowed only for a locally classified transient Groq timeout,
connection failure, rate-limit response, or provider 5xx/unavailable response.
It is never allowed for authentication, configuration, disabled-feature,
permission, chat/HMAC/replay, object-scope, unsafe-input, prompt-injection,
schema, citation, validation, quota, token/step/time budget, cancellation,
stale-state, duplicate, or business-rule failures. Existing same-provider
retries remain bounded and cannot reclassify an ineligible failure.

A Telegram request may transition once from Groq to LM Studio. A Phase 17 run
may transition once at any provider turn. Before transition the application
rechecks current authorization, feature/configuration state, remaining budget,
and that no result for the failed turn was accepted. A Recovery run persists
the exact approved local provider/model pair before its first local request so
retries cannot return to Groq; Telegram keeps the selected local pair for the
remainder of the request. Neither path ever switches back
to Groq or to another model. Local unavailability or invalid local output uses
the existing bounded failure path.

The transition stores only stable safe metadata: source and target provider/
model, reason code, sequence, and timestamp. Existing protected records and
audit structures are reused. One reviewed migration extends the protected
Project Recovery `AgentRun.model_code` constraint for the approved Qwen code.
Provider-reported usage
or a conservative nonzero estimate is accumulated across primary, retries,
and fallback under the existing feature/run budgets. Raw prompts, evidence
envelopes, provider responses/errors, reasoning, secrets, and chat identifiers
are not retained as transition metadata.

The exact local model artifact and reasoning setting must pass the Phase 21 Arabic/English strict-
schema, citation, agent-decision, security, quality, latency, cancellation,
and concurrency evaluation before enablement and after any relevant model,
quantization, LM Studio, schema, or prompt-version change. Local inference has
an effective concurrency of one. A deterministic fake server covers automated
tests; live model evaluation is an explicit operator step and never silently
downloads a model.

Deployed staging and production remain Groq-only under Decision 0023 until a
separate approval covers suitable inference infrastructure, availability,
capacity, monitoring, patching, data residency, and operational ownership.

## Supersession

This decision supersedes only the Groq-only provider selection, Groq-secret
requirement, and HTTPS-provider-endpoint language in Decisions 0020, 0021,
0022, and 0024 for this loopback-only local-development path and controlled
fallback. It does not supersede their feature scope, evidence exclusions,
recipient restrictions, permissions, schemas, citations, proposal/HITL rules,
execution controls, auditing, privacy, retention, or production requirements.
Decision 0023 continues to govern staging and production.

## Consequences

- Telegram and agent analysis can continue through the local model during an
  approved transient Groq outage while the computer and LM Studio are running.
- One-way pinning makes a mixed-provider agent run reproducible and prevents
  oscillation or retry storms.
- Local execution removes the external provider hop for fallback data but does
  not make model output authoritative or grant the model database access.
- The laptop processes local requests serially; local answers may be slower and
  remain unavailable when the host, LM Studio server, or model is stopped.
- Operators must install the model explicitly, run the capability gate, keep
  the endpoint loopback-only, and use the documented launcher/runbook.
- Disabling fallback or LM Studio leaves every non-AI workflow intact and
  preserves all protected AI and audit evidence.
