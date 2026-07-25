# ADR 0004: Private Object Storage in Production

- Status: Accepted
- Date: 2026-07-23
- Source: Approved scope and development playbook

## Context

Production application filesystems are ephemeral and uploaded files may
contain sensitive company or personal information.

## Decision

Use private S3-compatible object storage in production. Use separate buckets
and credentials for staging and production. File access must be authorized
before issuing short-lived access URLs.

## Consequences

- Upload metadata is stored in PostgreSQL while file bytes live in object
  storage.
- Upload size, extension, and MIME type are validated before acceptance.
- Buckets are private, encrypted, and covered by approved lifecycle rules.
- Local development storage may use a private local directory, but production
  may not depend on the container filesystem.
