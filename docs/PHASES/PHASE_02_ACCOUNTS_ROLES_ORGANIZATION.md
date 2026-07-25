# Phase 2: Accounts, Roles, and Organization

Status: Draft; blocked by permission and lifecycle decisions.

## 1. Goal

Implement approved internal account administration, departments, predefined
Django groups, authentication lifecycle, role-aware navigation, and auditable
account changes.

## 2. Included Features

- Approved user profile fields and department association.
- Departments.
- Admin-created accounts; activation and deactivation.
- User-facing login and logout.
- Approved predefined Django groups and permission assignments.
- Role-aware navigation backed by server authorization.
- Audit events for account lifecycle and role changes.
- Approved per-user language preference and fully localized Arabic/English
  account, authentication, navigation, and department screens.

## 3. Excluded Features

- Custom permission-builder UI.
- Public registration, social login, and external-trainer accounts.
- Projects, courses, tasks, attendance, and later domain navigation.
- Any permission not present in the approved matrix.
- Unapproved Arabic translations for role or department terminology.

## 4. User Stories

- As an authorized administrator, I can create, assign, deactivate, and
  reactivate internal accounts.
- As an active user, I can sign in and sign out securely.
- As an inactive user, I cannot sign in or retain protected access.
- As an authorized auditor, I can rely on an audit record of lifecycle and
  group changes, subject to approved audit visibility.

## 5. Models Involved

- `accounts.User` additions approved for Phase 2.
- `organizations.Department`.
- Django `Group` and `Permission`.
- `audit.AuditEvent` or an equally explicit append-only audit model.
- User language preference only if `L10N-01` approves persistence.

Exact fields wait for the approved permission/profile decisions.

## 6. Pages Involved

- Login/logout.
- Authorized account list, create, detail/edit, deactivate/reactivate.
- Department list/create/edit/archive as approved.
- Account role/group assignment.
- Base navigation updated for approved capabilities.

## 7. Permission Requirements

Blocked until `RBAC-01`, `RBAC-02`, `RBAC-04`, `RBAC-08`, and relevant audit
visibility are approved. Permissions must be checked in views, services, and
querysets; navigation visibility is not enforcement.

## 8. Validation Rules

- Unique identity fields and normalized input follow the approved account
  policy.
- Arabic identity/search normalization follows `L10N-04` and never destroys
  the stored original name.
- Passwords use Django validation and hashing.
- Only authorized actors may assign privileged groups.
- Inactive accounts cannot authenticate.
- Archive/hard-delete behavior follows approved `BR-16`.

## 9. Business Rules

- Accounts are created by authorized administrators.
- Inactive users cannot sign in.
- Lifecycle and role changes create audit records.
- Exact predefined group permissions and object visibility remain unresolved.

## 10. Expected Migrations

- Approved Phase 2 fields on `accounts.User`.
- Initial `organizations.Department`.
- Initial audit-event model if it is not otherwise available.
- Constraints/indexes for approved identity, department, archive, and audit
  queries.

## 11. Unit Tests

- Account forms and password validation.
- Activation/deactivation services.
- Group assignment policy.
- Audit payload safety.
- Language preference and localized role-label mapping.

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

- Approved account and department lifecycle works.
- Predefined groups exactly match the approved matrix.
- View- and object-level permissions are enforced and tested.
- Inactive users cannot authenticate.
- Passwords are hashed and security-relevant changes are audited.
- No later business domain is implemented.
- Arabic and English account workflows pass localization/RTL verification.

## 17. Dependencies

- Completed Phase 1.
- Approved full permission matrix and object-level questions.
- Approved identity fields, account lifecycle, archive/hard-delete, audit
  visibility, and login-security policy.
- Approved default/preference, terminology owner, and identity normalization
  rules.

## 18. Rollback Considerations

- Preserve user identity and audit history.
- Role/group seed changes require reversible data migrations or documented
  forward fixes.
- Do not drop account fields or departments with data without an approved
  export/backfill plan.
