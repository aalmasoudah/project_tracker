# Decision 0016: Phase 11 Notifications and Background Jobs

Status: Approved on 2026-07-29.

- Phase 11 categories are task assignment, approval, deadline/overdue, and
  mention. The approval category is mandatory in-app; users may independently
  disable in-app or email delivery for the other categories and may disable
  approval email.
- Assignment notifications go only to newly active assignees. Completion and
  attendance approval notifications go only to the current approver, followed
  by a generic update to the submitter or trainer-link issuer. Mentions notify
  active users only when they can access the task at event time.
- Task reminders run at 08:00 Asia/Riyadh. An active assignee receives one
  reminder on the day before the due date and one reminder on each overdue
  day. Completed, cancelled, archived, or cancelled-owner-context tasks do not
  generate reminders. Phase 11 adds no escalation chain.
- Notification titles and bodies are fixed, generic Arabic/English content.
  They do not contain record names, comments, personal information, or other
  sensitive payloads. Stored links are validated local application paths;
  target authorization is rechecked by the destination view.
- Each recipient/event key is unique. Domain writes and notification creation
  share the domain transaction, while email delivery starts only after commit.
  Email failure does not roll back the business event.
- Django's email abstraction uses console delivery in development, in-memory
  delivery in tests, and required authenticated SMTP configuration in
  production. Recipient language selects a complete RTL Arabic or LTR English
  multipart email.
- Celery uses Redis, bounded exponential retries, a protected delivery record,
  recovery of interrupted work, and safe error-class metadata. Technical
  Admin is the only role with the delivery-status permission.
- Notifications, preferences, and delivery records are protected from normal
  hard deletion. Final retention and purge rules remain deferred to Phase 14.
- SMS, chat, push notifications, escalation chains, and provider-specific
  integrations remain outside Phase 11.
