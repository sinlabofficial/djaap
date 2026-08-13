# ADR-0005: Platform Runtime Reliability and Operational Logs

## Status

Accepted

## Date

2026-08-14

## Context

Some deployments need deferred tasks, inbound webhooks, realtime
notifications, and operational lifecycle evidence. The starterkit must expose
stable contracts without forcing a specific worker, broker, scheduler, or
observability vendor.

## Decision

djaapp provides one generic `platform_runtime` boundary for Background Tasks,
Webhook Events, Realtime Events, and Runtime Logs. Domain Apps own business
semantics; Platform Runtime owns infrastructure contracts and operational
records.

All side-effecting tasks must be retry-safe and idempotent, using a state guard
or stable Idempotency Key/event identifier. Database changes use atomic
transactions. Tasks and realtime notifications are scheduled through
`transaction.on_commit()` so they cannot observe work that later rolls back.

Inbound webhooks are verified and deduplicated before processing. Realtime is
best-effort notification only; HTTP/HTMX remains the authoritative state
channel. Audit Logs and Runtime Logs remain separate, with redaction,
retention, pagination, and RBAC-aware access.

The baseline does not require Celery, Django-Q, Redis, Channels, a scheduler,
or a managed observability product. Production enables an explicit adapter when
the deployment needs that capability.

## Consequences

- Domain Apps can consume stable public runtime interfaces without owning
  infrastructure details.
- Retry, timeout, idempotency, redaction, and post-commit behavior are part of
  the operational contract.
- Deployments must document and configure worker, scheduler, broker, realtime,
  alerting, and retention responsibilities when enabled.
- Runtime evidence must never contain credentials or unrestricted sensitive
  payloads.

## Rejected alternatives

- Making Celery, Redis, or Channels mandatory was rejected to keep the
  starterkit backend-neutral and incrementally deployable.
- Combining Runtime Logs with Audit Logs was rejected because their purpose,
  retention, and access patterns differ.
- Durable WebSocket delivery was rejected for the baseline; clients can
  recover authoritative state through HTTP/HTMX.
