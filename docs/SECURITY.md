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
  the exact control is specified in the phase that owns login.

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

The permission matrix and object-level access policy are unresolved and block
Phase 2 and every later user-facing domain phase.

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
- Rotate expiry on rejection while reopening the same logical link as required.
- Make approved attendance read-only through the external link.
- Record issue, submission, rejection, approval, expiry, and correction events
  without recording the raw token.

The exact expiry duration and expiry-during-entry behavior require approval.

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

## Open Security Decisions

- Complete role and object-level permission matrix.
- Personal attendance visibility and export authorization.
- Default language, persisted preference, and approved Arabic terminology.
- Arabic normalization rules for identity, duplicate detection, and search.
- Authorized reject/reopen/correct/override actors.
- Trainer-link expiry duration and expiry-during-entry behavior.
- Allowed upload classes and size limits for each workflow.
- Retention and hard-deletion policy.
- Notification categories and sensitive email content policy.
- Operational owners, escalation contacts, and required compliance controls.
