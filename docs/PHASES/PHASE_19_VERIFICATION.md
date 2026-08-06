# Phase 19 Verification

Verified locally on 2026-08-06.

## Automated quality gate

- `ruff format --check .`: passed; 364 files already formatted.
- `ruff check .`: passed.
- `mypy .`: passed for 294 source files.
- `python manage.py check`: passed with no issues.
- `python manage.py makemigrations --check --dry-run`: passed; no missing migrations.
- `pytest tests/unit tests/integration -q`: 228 passed.
- `pytest tests/browser -q`: 16 passed in Google Chrome.
- `git diff --check`: passed.

## Phase acceptance evidence

- Arabic and English bounded executive questions are validated before queueing.
- Unsupported, unsafe, credential-seeking, prompt-injection, write, URL, file,
  shell, SQL, web, trainee, and attendance requests are rejected locally.
- Evidence is permission-scoped, deterministically ranked, size limited, and
  excludes names and the other protected domains listed in the phase boundary.
- Groq uses strict structured output, the configured 120B model by default,
  validated citations, retry/repair limits, token accounting, and safe errors.
- Requests are CEO/chat scoped, HMAC signed, replay protected, audited,
  idempotent, quota limited, asynchronously processed, and stale recoverable.
- The n8n workflow preserves fixed PDF/report commands and routes ordinary
  Telegram text through the signed assistant start/status flow.
- The imported local n8n workflow is published with its Telegram credential
  reference and contains no source-controlled credential or API key.

## Provider and runtime verification

- A live Groq 120B structured request succeeded with 26 bounded sources and
  valid citations.
- A production-style queued request completed through Celery with the Groq
  provider and produced a Telegram-safe cited answer.
- Django health, Celery task registration, database migration, and the
  published n8n workflow were verified locally.

## Remaining operator check

End-to-end delivery through Telegram requires one message from the configured
CEO account while the temporary tunnel, Django, Celery, Redis, and n8n are
running. This is an external manual delivery check, not an implementation gap.
The local quick-tunnel address is temporary and must be replaced by a stable
HTTPS deployment for production.
