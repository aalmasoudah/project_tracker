# Test Strategy

## Status and Goals

Status: Planning baseline.

Tests protect business rules, authorization, data integrity, migrations,
critical browser workflows, and production configuration. PostgreSQL is used
for every automated Django test; SQLite is prohibited.

## Test Layers

### Unit Tests

- Pure validators, forms, services, selectors, calculations, token utilities,
  and policy functions.
- Boundary values, invalid values, archived records, and retry behavior.
- Centralized progress functions receive exhaustive scenario coverage after
  their formulas are approved.

### Integration Tests

- Django views, middleware, templates, ORM constraints, transactions,
  permissions, imports, storage adapters, and background job boundaries.
- PostgreSQL-specific constraints and concurrency-sensitive workflows.
- Query-count tests for list pages, dashboards, search, and approval queues.

### Browser Tests

Playwright covers critical user journeys, not every rendering permutation:

- Authenticated shell and health smoke checks in Phase 1.
- Login, inactive-user denial, and role navigation in Phase 2.
- One approved create/edit/archive path for each major domain.
- Import preview/confirm, trainer-link submission, attendance review, and
  correction lifecycles.
- Dashboard/search authorization and required report generation.

Browser tests use synthetic users and data. They may create sessions through
test-only fixtures but must never add production test backdoors.

Every critical browser workflow runs in the language(s) needed to prove both
English LTR and Arabic RTL behavior. At minimum, each phase exercises its main
workflow in Arabic and verifies that language/direction remain correct across
full-page and HTMX responses.

### Security Tests

- Anonymous, inactive, wrong-role, and wrong-object denial.
- Direct URL access and queryset information leakage.
- CSRF and HTTP method enforcement.
- Upload validation and private download authorization.
- Token entropy assumptions, hash lookup, expiry, replay, and read-only state.
- Sensitive information absent from logs, errors, and health responses.
- Production settings and `DEBUG=False` checks.
- Bidirectional user content cannot visually escape its component or corrupt
  surrounding labels/actions.
- For Phase 17, verify exact tool/action allowlists, strict schemas/citations,
  forged-ID rejection, prompt-injection resistance, current-scope rechecks,
  stale/expired/revoked paths, approval/rejection, transactional rollback,
  duplicate execution, token/step/result/quota limits, provider retry
  classification, reviewed memory, and n8n HMAC/replay/idempotency.

### Localization Tests

- Translation catalogs contain every new user-facing string and compile.
- Arabic and English validation/error messages render in the active language.
- Root and fragment directionality is correct.
- Arabic names, comments, filters, imports, exports, and search round-trip
  without text loss.
- Mixed Arabic/Latin identifiers, long Arabic labels, pluralization, and empty
  states are covered.
- Reports are rendered to images and inspected for Arabic shaping, font
  embedding, RTL order, clipping, and pagination.
- Exercise the Phase 17 request/timeline/proposal/verification/review flow in
  Arabic RTL mobile and verify English LTR rendering and translated
  validation/status text.

## Tooling

- `pytest` and `pytest-django` for unit/integration tests.
- `pytest-xdist` only if parallel execution is proven safe with the PostgreSQL
  test setup.
- Playwright for supported-browser critical workflows.
- Ruff for formatting and linting.
- mypy with Django-aware configuration for type checking.
- Django `check`, `check --deploy`, and `makemigrations --check`.
- Dependency and static security scanning before production deployment.

The exact coverage-reporting threshold may be added after baseline measurement;
phase completion depends on acceptance-criterion coverage, not a vanity
percentage.

## Test Organization

```text
tests/
  conftest.py
  unit/
  integration/
  browser/
  security/
```

Tests may also live beside a domain app when that becomes the established
project pattern. Choose one pattern in Phase 1 and use it consistently.

Markers should separate browser, slow, integration, and security suites.
Unmarked tests should remain fast enough for local feedback.

## Database and Fixtures

- CI starts an isolated PostgreSQL service.
- Test settings require a test database URL and fail clearly if it is absent.
- Factories/fixtures use fictional data and explicit role assignments.
- Transaction tests are used only when transaction boundaries or locking are
  under test.
- Tests clean up files, database records, and task state they create.
- No test silently connects to development, staging, or production databases.

## Migration Testing

Every model phase:

1. Reviews migration files.
2. Runs `makemigrations --check`.
3. Applies migrations to an empty PostgreSQL database.
4. Tests important constraints.
5. Adds forward/backward data-migration tests when data transformation exists.
6. Documents rollback limitations for irreversible operations.

Before release, a clean-install workflow builds the image, creates a fresh
database, applies migrations, runs checks, and executes the relevant suite.

## Quality Gate

The local and CI gate is:

```text
ruff format --check .
ruff check .
mypy .
python manage.py compilemessages
python manage.py check
python manage.py makemigrations --check
pytest
required Playwright workflows
```

Before production, also run deployment checks, dependency/security scans, and
the approved smoke suite. A failed required check blocks phase completion.
Flaky tests are defects and may not be ignored or retried into a passing claim.

Phase 15 additionally tests strict JSON/schema and citation validation, prompt
injection treatment, provider allowlisting, Groq request shape without tools,
cached-token accounting, evidence exclusions, role/object isolation, request
quota serialization, protected retention, idempotent processing, stale-worker
recovery, audit/notification side effects, and Arabic mobile plus English UI
presentation.

Phase 16 additionally tests HMAC canonicalization, timestamp and nonce replay
boundaries, exact CEO/chat authorization, bounded strict JSON, one-time PDF
downloads, named attendance only in the local PDF rows, aggregate-only Groq
evidence, critical-alert fingerprint/lease/acknowledgement behavior, safe
audit metadata, and static import/security assertions over the inactive n8n
workflow. Staging UAT exercises all four Arabic commands and a failed-delivery
retry using fictional names.

## Manual Verification

Each phase specification lists reproducible manual checks with:

- Preconditions and fictional test data.
- Actor/role.
- Exact steps.
- Expected result.
- Actual result and pass/fail.
- Notes or screenshots when useful.
- Language/locale used and Arabic reviewer where translation quality matters.

Manual verification complements automated tests; it does not replace them.

## Traceability

At the end of each phase, map every phase acceptance criterion to
implementation and automated/manual evidence. Before production, create the
full `docs/REQUIREMENTS_TRACEABILITY.md` requested by the playbook.

Phase 17 evidence is recorded in
`docs/PHASES/PHASE_17_VERIFICATION.md`; the operator and staging adversarial
workflow is in `docs/RUNBOOKS/PHASE_17_PROJECT_AGENT.md`.
