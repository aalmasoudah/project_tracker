# Decision 0024: Bounded Telegram AI Executive Assistant

Date: 2026-08-06

Status: Approved

## Decision

Phase 19 extends the CEO-only Telegram integration with standalone natural-
language executive questions. It does not change Phase 16 fixed commands and
is not an unrestricted chatbot. Only the exact configured active CEO/chat pair
may ask questions, and every signed request retains the Phase 16 HMAC,
freshness, nonce, body-size, and replay controls.

Django validates each question locally, selects and ranks permission-scoped
project/task/approval evidence, and sends only a bounded safe subset plus the
question to Groq. The provider has no tools and returns strict structured data.
Every factual finding and recommendation requires an allowlisted citation,
which Django resolves to a safe business label before Telegram delivery.

The assistant is read-only. It cannot access budgets, people, trainee or
attendance data, comments, files, credentials, raw audit metadata, environment
configuration, shell, SQL, web, code execution, or arbitrary HTTP. It has no
multi-turn memory and cannot execute Phase 17 proposals. Prompt-injection,
secret-seeking, personal-data, unsupported, and unknown slash-command inputs
fail closed before any provider call.

## Consequences

- The earlier arbitrary-command exclusion receives this narrow Phase 19
  exception only.
- Natural-language questions are stored as protected validated business input
  to support asynchronous processing; full provider prompts/envelopes and raw
  errors are never stored or logged.
- A separate feature flag, quota, token cap, evidence cap, and permission allow
  rollback without disrupting Phase 16 reports and alerts.
