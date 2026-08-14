# ADR 0020: Phase 15 AI Project Briefings

- Status: Approved
- Date: 2026-08-04

## Context

Insight Tracker needs a useful, controlled LLM feature without creating an
unrestricted chatbot or allowing generated text to change business records.
The existing application already owns authoritative project visibility,
progress, task, milestone, approval, audit, notification, and background-job
patterns.

## Decision

Create a dedicated `ai_briefings` Django domain. It builds permission-scoped,
allowlisted project evidence before any provider call, invokes Groq Chat
Completions asynchronously, validates a strict JSON Schema and local citation
allowlist, and stores the result as a read-only draft.

The production default model is `openai/gpt-oss-120b`. Administrators may
explicitly select `openai/gpt-oss-20b` through environment configuration.
Other model identifiers are rejected. The endpoint is fixed to Groq's HTTPS
OpenAI-compatible API and the secret is read only from `GROQ_API_KEY`.

The feature is disabled by default. Development and tests use a deterministic
fake provider. The provider receives no tools, browsing, code execution,
uploads, credentials, raw audit metadata, budget, trainee, attendance,
comments, or file contents. Generated output cannot execute application
actions.

Briefings and their safe source references follow the existing indefinite
retention decision and reject normal hard deletion.

## Consequences

- Output remains explainable through internal evidence links and review state.
- Current project permission is rechecked on request, generation, reading, and
  review.
- Groq outages and schema errors fail safely without blocking core workflows.
- The application needs a Celery worker and Redis when live generation is
  enabled.
- General chat, cross-project portfolio briefing, autonomous actions, external
  web retrieval, and custom prompt entry require separately approved phases.
