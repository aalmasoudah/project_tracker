# Security Plan

## Status and Security Objectives

Status: Planning baseline.

The system must protect company operations, personal trainee and attendance
data, budgets, files, approvals, credentials, and audit history. Security is
enforced on the server and at the database/storage boundaries; hidden
navigation is never an authorization control.

## Trust Boundaries

- Internal authenticated users accessing the Django application.
- External trainers accessing only a narrow, expiring attendance workflow.
- Browser-to-Django HTTP requests protected by HTTPS and CSRF controls.
- Django-to-PostgreSQL connections using environment-provided credentials.
- Django/worker-to-private-object-storage access using restricted credentials.
- Django/worker-to-email, Redis, and monitoring providers introduced only in
  approved phases.
- Phase 16 n8n-to-Django signed requests and n8n-to-Telegram delivery for one
  fixed private CEO chat; n8n receives no PostgreSQL or Redis credential.
- CI, staging, and production are separate environments with separate secrets
  and data.

## Authentication

- Use Django password hashing and session authentication.
- Create accounts only through an authorized administration workflow.
- Reject inactive users at authentication and authorization boundaries.
- Rotate the session identifier on login and rely on Django logout/session
  invalidation behavior.
- Do not log passwords, reset values, session identifiers, authorization
  headers, raw attendance tokens, or secret environment values.
- Add login rate limiting and abnormal-failure monitoring before production;
  Phase 2 uses five account failures or twenty IP failures in fifteen minutes
  followed by a fifteen-minute lock.
- Sessions expire after eight hours and when the browser closes.
- Logout, deactivation, password change, and administrative reset revoke
  applicable sessions.

External trainer links are capability URLs, not general accounts. They grant
only the approved session action and never internal navigation.

## Authorization

- Check model-level and object-level permissions in every view and service.
- Filter querysets to records the actor is allowed to discover.
- Return safe denial/not-found responses without leaking restricted record
  details.
- Recheck authorization at write time inside multi-step services.
- Test horizontal access, vertical privilege escalation, direct-object URLs,
  archived records, exports, and files.
- Keep the Django admin restricted to authorized technical administration.

The Phase 2 permission slice was approved on 2026-07-25. The Phase 3 project
slice was approved on 2026-07-26. Later domain permissions remain unresolved
and block their user-facing phases.

## Web Security

- Keep Django CSRF middleware enabled and include CSRF tokens in standard and
  HTMX forms.
- Escape untrusted template output by default; review any deliberate safe HTML.
- Validate redirects and never accept arbitrary external return URLs.
- Use secure response headers and clickjacking protection.
- Isolate user-controlled bidirectional text in templates so Arabic/Latin
  mixtures cannot visually spoof surrounding labels, identifiers, or actions.
- Set `DEBUG=False` in production and never expose stack traces.
- Enforce HTTPS, secure session/CSRF cookies, approved hosts, and approved
  trusted origins in production.
- Enable long-duration HSTS only after the final domain and HTTPS behavior are
  verified.
- Keep state-changing operations on non-GET methods and use confirmation
  screens for high-impact actions.

## Inputs and Files

- Validate all user input with Django forms or equivalent server-side
  validators.
- Apply database constraints for critical invariants.
- Limit request and upload sizes.
- Validate upload extension, declared MIME type, detected MIME type, and
  approved file class.
- Generate storage keys independently of user-provided filenames.
- Keep production buckets private and authorize every download.
- Prevent inline execution of unsafe content through response disposition and
  content-type handling.
- Add malware scanning only if an approved risk decision or file workflow
  requires it; do not imply that MIME validation is malware detection.

## Attendance Token Design

- Generate tokens with a cryptographically secure random source and sufficient
  entropy.
- Store a one-way token hash where practical and compare safely.
- Bind each token to one approved session/workflow.
- Enforce expiry and state on every read and write.
- Do not reveal whether guessed tokens were close or previously valid.
- Reopen the same logical link for 72 hours after a reasoned rejection.
- Make approved attendance read-only through the external link.
- Record issue, submission, rejection, approval, expiry, and correction events
  without recording the raw token.

Decision 0014 requires expiry to be rechecked at submission; decision 0015
defines the 72-hour rejection expiry.

## Secrets and Configuration

- Commit `.env.example` with names and safe placeholders only.
- Store real secrets in local ignored files or the platform secret manager.
- Use different credentials for development, CI, staging, and production.
- Give database, object-storage, email, monitoring, and Redis identities only
  the access required by their process.
- Document rotation and revocation procedures.
- Run dependency and security scanning in CI before production release.

## Audit and Privacy

Security-relevant events include authentication failures, account lifecycle
changes, role changes, restricted exports, archive/restore operations, token
events, approvals, attendance corrections, and protected operational commands.

Audit data must be append-only through normal application paths, access
controlled, correlation-friendly, and free of secrets. Retention, hard-delete
exceptions, export rights, and personal-data access require owner approval.

Technical Admin alone may read Phase 2 audit records. Accounts, departments,
and audit records are not hard-deleted. Expired throttle counters may be
deleted as temporary security data.

Phase 3 project audit is separated from the security scope. CEO and Executive
Manager may read all project history; a Project Manager may read history only
for a managed project. Technical Admin does not gain project-business access.
Projects and reference records are archived, and membership removal is
end-dated. Project uploads are deferred, so Phase 3 introduces no file attack
surface.

## Security Verification

Every applicable phase includes:

- Anonymous and inactive-user denial tests.
- Model-level and object-level authorization tests.
- Direct-object reference and queryset-leakage tests.
- CSRF and method-safety coverage for state changes.
- Validation and database-constraint tests.
- Sensitive-value log/output checks.
- Token expiry/guessing/replay tests for external links.
- Upload validation and unauthorized-download tests for file phases.
- Production settings checks and dependency/security scans before deployment.

## AI Briefing Security Boundary

- Project permissions are checked on request, worker execution, viewing,
  source navigation, and review.
- Only allowlisted, compact evidence leaves the application. Budget, task
  descriptions/comments/files, trainee/attendance records, credentials,
  tokens, environment values, and raw audit metadata are excluded.
- Database text is untrusted prompt data. Groq receives strict structured-
  output instructions and no tools, browsing, code execution, or action hooks.
- Local schema and citation validation is mandatory even when provider-side
  strict schema succeeds. Django escapes all generated text.
- Provider secrets, prompts, evidence payloads, generated content, and raw
  errors are excluded from logs and audit metadata.
- A disabled or unsafe provider configuration fails closed without changing
  business records.

## CEO Telegram and n8n Security Boundary

- The integration is disabled by default and is not a general public API or
  free-form chatbot. Only fixed read-only report and alert operations exist.
- Every n8n JSON request is body-bounded and authenticated with HMAC-SHA256,
  a five-minute timestamp window, a one-use hashed nonce, the exact configured
  private chat ID, and one fixed active CEO account/permission.
- PDF links contain a signed report/chat binding, expire after ten minutes,
  download once, and render in memory. They are never stored as uploads.
- Attendance PDFs may contain the explicitly approved trainee full name and
  attendance status. Groq receives only attendance aggregates; phone, email,
  notes, comments, files, chat identifiers, and tokens remain excluded.
- Critical alerts use protected fingerprints, leases, and acknowledgements so
  retries do not silently mark undelivered messages complete or change tasks.
- n8n saves neither successful nor failed workflow execution data. The bot
  token stays in the native credential store and the signing secret is
  injected from the deployment secret manager, never workflow JSON.

## Telegram AI Assistant Security Boundary

- Phase 19 is a separate opt-in extension of the exact Phase 16 CEO/chat and
  signed-request boundary. It does not make the integration public.
- Questions are standalone, length/topic bounded, idempotent by hashed message
  key, and locally rejected for injection, secrets, personal data, URLs/web,
  shell/SQL, files, attendance/trainees, or business writes before Groq.
- Evidence is permission-scoped and locally risk-ranked. It excludes budgets,
  people, comments, files, attendance, trainees, credentials, environment, and
  raw audit data. Groq receives no tools or conversation history.
- Strict schema and citation validation run locally. Telegram receives only a
  bounded plain-text answer with resolved safe source labels.
- Protected lifecycle records retain the validated question and safe answer
  but never the provider prompt/envelope, chain-of-thought, chat/message ID,
  credential, or raw error. Audit/log metadata contains codes and counts only.

## Project Recovery Agent Security Boundary

- Phase 17 is separate from the Phase 15 read-only/no-tools workflow. It uses
  seven exact read tools and five proposal codes; no shell, SQL, filesystem,
  web, arbitrary URL/HTTP, code, credential, file, raw-audit, trainee, or
  attendance capability exists in its registry.
- Goal, language, model, decision shape, tool/action code, arguments, payload,
  IDs, citations, step count, token/time budget, result size, request quota,
  and proposal lifetime are allowlisted or bounded server-side. Database and
  optional-context strings are labelled untrusted prompt data.
- Authorization and current object scope are rechecked at request, each tool,
  proposal creation, decision, execution, and verification. Possession of a
  run/proposal ID or earlier access grants nothing.
- Model output can create only a pending proposal. An authorized human must
  approve with a reason, and the approver becomes the execution actor. The
  current Phase 17 and underlying domain permissions are both required.
- Execution locks the proposal and target, validates the before-state
  fingerprint, calls the existing transaction-safe domain service, and reads
  the after state. Stale, expired, revoked, invalid, or duplicate attempts do
  not bypass completion approval or create a partial/second write.
- Only explicitly reviewed completed runs create same-project memory. Stored
  records omit chain-of-thought, full prompts, secrets, raw provider payloads,
  and raw errors; rendered provider/database text remains escaped.
- The optional n8n path uses HMAC-SHA256 over method/path/body, short
  timestamps, one-use hashed nonces, leased events, a human checkpoint, and an
  idempotent signed callback. Its export is inactive, contains no credential,
  and disables execution-data retention.

## Open Security Decisions

- Complete each later-domain role and object-level permission slice.
- Any attendance delivery outside the approved Phase 16 bound CEO chat.
- Default language, persisted preference, and approved Arabic terminology.
- Arabic normalization rules for identity, duplicate detection, and search.
- Authorized reject/reopen/correct/override actors.
- Trainer-link expiry duration and expiry-during-entry behavior.
- Allowed upload classes and size limits for each workflow.
- Retention and hard-deletion policy.
- Notification categories and sensitive email content policy.
- Operational owners, escalation contacts, and required compliance controls.
