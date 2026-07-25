# ADR 0002: PostgreSQL From the Start

- Status: Accepted
- Date: 2026-07-23
- Source: Approved scope, business rules, and development playbook

## Context

The application requires reliable transactions, constraints, indexes,
concurrency, approval workflows, imports, and production backup tooling.
Changing database engines after development would hide compatibility problems.

## Decision

Use PostgreSQL for development, automated tests, staging, and production.
SQLite is not an allowed fallback.

## Consequences

- Local development and CI require an available PostgreSQL service.
- Tests exercise PostgreSQL-specific behavior and constraints.
- Database URLs and credentials come from environment variables.
- Migrations are reviewed before application and are never generated against
  a different database engine.
