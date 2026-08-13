# ADR-0004: Optional REST API Adapter

## Status

Accepted

## Date

2026-08-14

## Context

External integrations and mobile clients may need HTTP APIs, but the dashboard
is the primary interface and the starterkit should not become API-first by
default. API behavior must not fork business rules or authorization policy.

## Decision

The `/api/` surface is an optional REST adapter using JWT authentication when
enabled. API serializers and viewsets validate transport shape and delegate
business reads and writes to the same public selectors and services used by
the dashboard.

The API is not a Domain App and does not own business models. API permissions
must enforce the same RBAC and object-level rules as dashboard operations.

## Consequences

- A client project can omit the API dependency and surface when no external
  integration is required.
- Dashboard and API clients share authoritative business behavior.
- API versioning, rate limiting, token rotation, and external exposure become
  deployment decisions when the adapter is enabled.
- An API endpoint must not be added merely to simplify internal dashboard CRUD.

## Rejected alternatives

- Making every capability API-first was rejected because it expands the
  baseline and duplicates internal presentation concerns.
- Allowing API viewsets to mutate models directly was rejected because it would
  bypass service invariants, audit, and transaction policy.
