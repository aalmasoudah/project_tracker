# Phase 2: Accounts, Roles, and Organization

Status: Completed and verified on 2026-07-25 after owner approval.

## 1. Goal

Implement approved internal account administration, departments, predefined
Django groups, authentication lifecycle, role-aware navigation, and auditable
account changes.

## 2. Included Features

- Required display name and email, immutable username, one primary department,
  one predefined role, forced temporary-password change, and persisted
  language preference.
- Departments.
- Admin-created accounts; activation and deactivation.
- User-facing login and logout.
- Seven approved internal Django groups and exact Phase 2 permissions.
- Role-aware navigation backed by server authorization.
- Audit events for account lifecycle and role changes.
- Persisted per-user language preference and fully localized Arabic/English
  account, authentication, navigation, and department screens.

## 3. Excluded Features

- Custom permission-builder UI.
- Public registration, social login, and external-trainer accounts.
- Projects, courses, tasks, attendance, and later domain navigation.
- Any permission outside the approved Phase 2 matrix.
- Later-domain Arabic terminology.

## 4. User Stories

- As an authorized administrator, I can create, assign, deactivate, and
  reactivate internal accounts.
- As an active user, I can sign in and sign out securely.
- As an inactive user, I cannot sign in or retain protected access.
- As an authorized auditor, I can rely on an audit record of lifecycle and
  group changes, subject to approved audit visibility.

## 5. Models Involved

- `accounts.User` additions for display name, required unique email,
  department, preferred language, forced password change, and lifecycle
  timestamps.
- Temporary PostgreSQL-backed login-throttle records.
- `organizations.Department`.
- Django `Group` and `Permission`.
- `audit.AuditEvent` or an equally explicit append-only audit model.
- Persisted Arabic/English user language preference.

## 6. Pages Involved

- Login/logout.
- Authorized account list, create, detail/edit, deactivate/reactivate.
- Department list/create/edit/archive as approved.
- Account role/group assignment.
- Base navigation updated for approved capabilities.

## 7. Permission Requirements

The approved matrix is recorded in `USER_ROLES.md` and decision 0007.
Permissions must be checked in views, services, and querysets; navigation
visibility is not enforcement. Only a superuser may assign Technical Admin.

## 8. Validation Rules

- Username is immutable, Unicode NFKC-normalized, and case-insensitively
  unique. Email and display name are required; email is case-insensitively
  unique.
- Arabic identity text is preserved. Derived search may ignore
  diacritics/tatweel and normalize Alef and Persian keyboard variants without
  merging `ة/ه` or `ى/ي`.
- Passwords use Django validation and hashing.
- Only authorized actors may assign privileged groups.
- Inactive accounts cannot authenticate.
- Accounts, departments, and audit records cannot be hard-deleted through the
  application.
- Five account or twenty IP failures in fifteen minutes cause a fifteen-minute
  lock with non-enumerating messages.
- Sessions expire after eight hours/browser close and are revoked on logout,
  deactivation, password change, or administrative reset as applicable.

## 9. Business Rules

- Accounts are created by authorized administrators.
- Inactive users cannot sign in.
- Lifecycle and role changes create audit records.
- Each internal account has exactly one managed group.
- Technical Admin administers accounts/departments and reads Phase 2 audit.
- CEO/Executive Manager view the active organization directory.
- Project Manager/Supervisor view active users in their own department.
- Employee/Contractor view only their profile and department.
- External Trainer has no internal account or group.

## 10. Expected Migrations

- Approved Phase 2 fields on `accounts.User` plus identity constraints.
- Initial `organizations.Department`.
- Initial append-only `audit.AuditEvent`.
- Temporary login-throttle storage.
- Reversible data migration seeding the seven approved internal roles and
  their Phase 2 model permissions.
- Constraints/indexes for identity, department, archive, throttle, and audit
  queries.

## 11. Unit Tests

- Account forms and password validation.
- Activation/deactivation services.
- Group assignment policy.
- Audit payload safety.
- Language preference, account-search normalization, and localized role-label
  mapping.

## 12. Integration Tests

- Login success/failure and logout.
- Inactive-user denial and session invalidation behavior.
- Authorized/unauthorized create, edit, group assignment, and lifecycle
  actions.
- Department-scoped queryset behavior.
- Audit records for every security-relevant change.
- Arabic names and localized validation round-trip through PostgreSQL.

## 13. Browser Tests

- Authorized admin creates a fictional user and assigns approved roles.
- Each approved role signs in and sees only permitted navigation in Arabic and
  English.
- Deactivated user is denied.

## 14. Security Tests

- Password hashes are never returned or logged.
- Privilege escalation through form tampering/direct URLs is denied.
- Cross-department/account visibility follows the approved matrix.
- Login CSRF, safe redirects, rate limiting, and failure messages avoid account
  enumeration.

## 15. Manual Verification

- Create fictional users for every approved role.
- Sign in/out as each role and verify navigation/denials.
- Deactivate/reactivate a user and inspect session/access behavior.
- Review lifecycle/group audit records with an authorized actor.
- Verify Arabic names, RTL forms, language persistence (if approved), and
  official role terminology.

## 16. Acceptance Criteria

- Approved account and department lifecycle works, including immediate session
  revocation.
- Predefined groups exactly match the approved matrix.
- View- and object-level permissions are enforced and tested.
- Inactive users cannot authenticate.
- Passwords are hashed and security-relevant changes are audited.
- No later business domain is implemented.
- Arabic and English account workflows pass localization/RTL verification.

## 17. Dependencies

- Completed Phase 1.
- Approved full permission matrix and object-level questions.
- Decision 0007 and the source-document updates approved on 2026-07-25.

## 18. Rollback Considerations

- Preserve user identity and audit history.
- Role/group seed changes require reversible data migrations or documented
  forward fixes.
- Do not drop account fields or departments with data without an approved
  export/backfill plan.
