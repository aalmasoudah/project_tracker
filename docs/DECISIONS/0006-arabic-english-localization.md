# ADR 0006: Arabic and English Localization

- Status: Accepted
- Date: 2026-07-23
- Source: Project-owner scope addition

## Context

The system must fully support Arabic. Deferring localization until report
development would embed left-to-right assumptions in templates, forms,
workflows, search, imports, and tests.

## Decision

Treat Arabic and English as first-class languages beginning in Phase 1. Use
Django internationalization, direction-aware Bootstrap layouts, locally served
Arabic-capable assets, and localized validation. Preserve original Arabic data
in PostgreSQL and verify critical workflows in RTL and LTR.

The default language, persisted preference, official terminology, calendar/
digit conventions, and normalization rules remain configurable or deferred
until the project owner approves them.

## Consequences

- Every user-visible phase includes translation and RTL/LTR acceptance
  criteria.
- Internal status/action identifiers remain stable and language-neutral.
- Imports, search, notifications, PDF/Excel reports, and operational pages
  require explicit Arabic verification.
- Builds compile translation catalogs and package Arabic-capable fonts/assets.
- Missing or broken Arabic behavior blocks completion of an affected phase.
