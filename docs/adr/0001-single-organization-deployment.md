# ADR-0001: Single-Organization Deployment Model

## Status

Accepted

## Date

2026-08-14

## Context

djaapp is a reusable starterkit for independently deployed client webapps. A
deployment serves one organization and is not a shared SaaS instance. Earlier
concepts such as Workspace, multi-workspace tenancy, data-platform domains, and
agent-runtime domains do not belong in the baseline.

## Decision

djaapp uses a single-organization deployment model. Organization settings are
singleton configuration for that installation, not a tenant registry. The
baseline includes identity, roles, permissions, RBAC, audit logging, the
server-rendered dashboard, and a replaceable Domain App example.

The API remains an optional adapter for external integrations or clients such
as mobile applications. The dashboard remains the primary application
interface.

## Consequences

- The baseline is simpler to install, explain, secure, and operate.
- Domain Apps must not introduce Workspace or tenant assumptions implicitly.
- A client project that needs SaaS tenancy must make that a deliberate
  architecture change rather than extending this baseline silently.
- A fresh installation is required when adopting this boundary; removed legacy
  Workspace, Data, or Agent models are not migration inputs.

## Rejected alternatives

- Shared multi-tenant SaaS was rejected because it adds isolation, routing,
  billing, and operational responsibilities outside the starterkit baseline.
- Keeping unused Workspace, Data, or Agent models was rejected because stale
  abstractions obscure ownership and increase installation complexity.
