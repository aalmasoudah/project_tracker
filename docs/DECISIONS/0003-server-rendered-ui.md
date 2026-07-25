# ADR 0003: Server-Rendered User Interface

- Status: Accepted
- Date: 2026-07-23
- Source: Approved scope and development playbook

## Context

The initial application is an internal workflow system. It needs accessible
forms, tables, dashboards, validation, and incremental interactions without
the cost of a separate API and frontend deployment.

## Decision

Use Django templates with Bootstrap 5 and HTMX. Responses remain usable
without unnecessary client-side state, and HTMX endpoints return server-owned
HTML fragments.

## Consequences

- Django forms remain the source of input validation.
- Full-page navigation and progressive enhancement are the default.
- CSRF protection applies to all state-changing HTMX requests.
- React and a public API remain outside the initial release.
