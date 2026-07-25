# 0007: Phase 2 Accounts, RBAC, and Localization Policy

Status: Accepted by the project owner on 2026-07-25.

## Context

Phase 2 was blocked by account identity, lifecycle, authorization, audit,
login-security, deletion, and localization decisions. Approving a complete
future-domain permission matrix before those domains have approved workflows
would force premature business decisions.

## Decision

### Permission planning

Permissions are approved one phase at a time. Phase 2 approves only accounts,
departments, authentication, and their audit records. Later domain permissions
remain blocked until their own phases.

The predefined internal roles are Technical Admin, CEO, Executive Manager,
Project Manager, Supervisor, Employee, and Contractor. Each internal account
has exactly one managed predefined role. External Trainer is not an internal
account or Django group.

Only a Django superuser may grant or revoke Technical Admin. Technical Admin
may administer non-superuser accounts, assign non-technical roles, manage
departments, and read Phase 2 audit records.

The approved Phase 2 read scopes are:

- CEO and Executive Manager: all active directory entries and active
  departments.
- Project Manager and Supervisor: active directory entries in their own
  department and their own department.
- Employee and Contractor: their own profile and own department.

All non-technical roles are read-only for Phase 2 organization data. No
Phase 2 approval or export permission exists.

### Identity and lifecycle

- Username is the immutable Unicode login identifier and is compared
  case-insensitively.
- Email and display name are required; email is unique case-insensitively.
- Each non-technical internal account has one primary department.
- Accounts persist an Arabic or English language preference.
- New or administratively reset passwords are temporary and require a password
  change at the next login.
- Deactivation revokes sessions immediately. Reactivation requires a new
  login.
- Technical Admin cannot deactivate itself or the last active administrator.
- Accounts are never hard-deleted.

### Departments

Departments have a stable unique ASCII code and required Arabic and English
names. Codes are never reused. Departments are archived rather than deleted,
cannot accept new users while archived, and cannot be archived while they
contain active users.

### Authentication security

- Five failed attempts for an account in fifteen minutes create a fifteen
  minute account lock.
- Twenty failed attempts from one IP in fifteen minutes create a fifteen
  minute IP lock.
- Authentication responses do not reveal whether an account exists.
- Successful authentication clears relevant counters.
- Authenticated sessions expire after eight hours and when the browser closes.
- Logout, deactivation, password changes, and administrative password resets
  revoke applicable sessions.
- Expired throttle counters are temporary security data and may be deleted.

### Audit

Login success, failure, lockout, and logout; account creation and profile
changes; activation/deactivation; administrative password reset; role and
department changes; and department creation/update/archive/restore are
audited.

Audit records are append-only through application paths, contain no password
values or hashes, are readable only by Technical Admin in Phase 2, and are not
hard-deleted. Retention remains a Phase 14 decision.

### Localization

Arabic is the application default. Users may persist Arabic or English.
Stored Arabic and mixed-direction names remain unchanged except for surrounding
whitespace trimming and username Unicode NFKC normalization.

Identity matching does not fold Arabic letters. Search may use a derived key
that ignores Arabic diacritics and tatweel and normalizes Alef and Persian
keyboard variants. It does not merge `ة` with `ه` or `ى` with `ي`.

The project owner is the official terminology approver. Approved Phase 2 role
terms are:

| Stable role | Arabic label |
| --- | --- |
| Technical Admin | مسؤول النظام التقني |
| CEO | الرئيس التنفيذي |
| Executive Manager | المدير التنفيذي |
| Project Manager | مدير المشروع |
| Supervisor | المشرف |
| Employee | الموظف |
| Contractor | المتعاقد |
| External Trainer | المدرب الخارجي |

## Consequences

- Phase 2 can proceed without guessing later-domain permissions.
- Later phases must extend the matrix explicitly and cannot infer access from
  role names.
- A superuser remains the recovery boundary for Technical Admin assignment.
- Role cardinality is intentionally one managed group per account.
- Arabic identity remains exact while search can be more forgiving without
  altering stored text.
