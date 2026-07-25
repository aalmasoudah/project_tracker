# ADR 0001: Django Monolith

- Status: Accepted
- Date: 2026-07-23
- Source: Approved scope and development playbook

## Context

The system contains tightly related internal workflows, authentication,
permissions, forms, approvals, reporting, and transactional data. The first
release does not require a public API or an independently deployed frontend.

## Decision

Build the initial release as a Django 5.2 LTS monolith on Python 3.13. Organize
the code into business-domain Django apps while keeping one deployable web
application and one PostgreSQL system of record.

## Consequences

- Django provides authentication, forms, ORM, migrations, templates, and
  security defaults in one stack.
- Domain boundaries remain explicit even though deployment is monolithic.
- Views stay thin; services own multi-model writes and selectors own complex
  reads.
- A public API or separate frontend requires a later approved decision.
