# Decision 0014: Phase 9 Sessions and Trainer Links

Status: Approved on 2026-07-29.

- Attendance values are Present, Absent, Late, and Excused; every locked
  session participant requires one value.
- Sessions use Asia/Riyadh, Gregorian dates, and Western digits. Daily and
  weekly recurrence is limited to 52 occurrences and is retry-safe. Multiple
  sessions per day are allowed.
- Only an active trainer assigned to the course is eligible. Issuing a link
  locks the active enrollment roster.
- Links default to 72 hours and allow 1 hour through 14 days. Submission
  rechecks expiry; expiry during entry commits nothing.
- Tokens contain 256 random bits. Only a SHA-256 hash is stored. Reissue
  revokes the prior token, raw links appear only on the no-store issuance
  response, and one session accepts one atomic submission.
- Evidence allows up to five private PDF/PNG/JPEG files, 10 MiB each.
- Executive Managers manage all sessions; Project Managers manage their
  courses; CEO and the owning Supervisor have read-only scoped views. External
  links reveal trainee number/name only.
