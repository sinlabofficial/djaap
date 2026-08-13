# ADR-0007: Explicit Production Deployment Contract

## Status

Accepted

## Date

2026-08-14

## Context

The starterkit must be deployable without assuming a particular cloud
provider. Web startup, migrations, background capabilities, backups, and
health evidence have different ownership and failure modes. Implicit startup
behavior makes releases unsafe when multiple web instances start together.

## Decision

Production uses an immutable runtime image and an external PostgreSQL service.
The web process is serve-only. A release runs the migration step exactly once
from the release image before scaling web processes. Worker, scheduler,
realtime, TLS, backup, alerting, and incident response are enabled only when
the deployment contract explicitly configures them.

Release verification must cover configuration, container startup, production
boot, migration readiness, health behavior, and documentation/toolchain parity.
Operational evidence must distinguish repository checks from staging or
production evidence.

## Consequences

- Multiple web instances do not race to mutate the database at startup.
- Deployments must provide an explicit migration, rollback, backup, and
  recovery procedure.
- A green image build does not by itself prove production readiness.
- Cloud-specific infrastructure remains outside the starterkit and must be
  documented by the adopting project.

## Rejected alternatives

- Running migrations on every web startup was rejected because it creates race
  conditions and couples serving to release mutation.
- Bundling a mandatory worker, broker, scheduler, or managed PostgreSQL was
  rejected to keep the baseline portable.
