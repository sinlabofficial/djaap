# djaapp Context

> Context version: 3.0.0 | Last reviewed: 2026-08-14

This document records the public product terminology and stable architectural
facts for the djaapp starterkit. It is the domain context for developers and
AI agents extending a fresh client project.

## Product shape

djaapp is a production-oriented Django full-stack webapp starterkit for one
organization per deployment. Django Templates render the primary dashboard,
HTMX handles server-backed interactions, Alpine.js handles local browser state,
and TailwindCSS provides styling through semantic design tokens. PostgreSQL is
the default production database and Docker provides the reproducible runtime
boundary.

Dashboard users authenticate with Django sessions. REST API endpoints are
optional adapters for external integrations or clients such as mobile
applications; djaapp is not API-first.

The baseline is intentionally generic. Workspace or multi-workspace tenancy,
data-platform capabilities, and agentic-AI runtime capabilities are outside
scope. A client project that needs one of these capabilities must introduce it
as an explicit architecture decision.

## Glossary

- **User**: An authenticated person. Email is the canonical username; phone
  and employee ID may also be supported as login identifiers.
- **Role**: A named access grouping with a hierarchy level.
- **Permission**: A granular access rule expressed as a `resource:action` pair,
  such as `users:view` or `roles:assign`.
- **RBAC**: Role-based access control. A user's effective permissions are the
  union of active role assignments; superusers bypass RBAC checks.
- **Organization Settings**: Singleton settings for the organization served by
  one deployment. They are not a tenant registry.
- **Dashboard**: The session-authenticated web interface rendered by Django
  Templates under `/dashboard/`.
- **API**: Optional REST endpoints under `/api/` for external integrations and
  clients. They adapt public Domain App interfaces.
- **Service**: A write-oriented operation boundary for business rules,
  transactions, state transitions, and side effects.
- **Selector**: A read-oriented operation boundary for queries and retrieval.
- **Domain App**: A Django app that owns one cohesive business concept,
  including its models, invariants, permissions, and public interfaces.
- **Client Deployment**: An independently deployed installation serving one
  client organization, not a shared SaaS instance.
- **Safe Delete**: Soft deletion that hides records from normal queries without
  immediately removing them physically.
- **Platform Runtime**: Generic infrastructure contracts for background tasks,
  inbound webhooks, realtime notifications, and Runtime Logs. It does not own
  Domain App business semantics.
- **Background Task**: A focused unit of deferred work designed to be safe to
  retry through the platform task interface.
- **Webhook Event**: An inbound provider event that is verified, deduplicated,
  and handed to a Domain App for processing.
- **Realtime Event**: A permission-filtered, best-effort notification published
  after a committed business change so a client can refresh authoritative
  state through HTTP/HTMX.
- **Audit Log**: A record of who changed business or access data and what action
  occurred.
- **Runtime Log**: A record of task, webhook, and realtime lifecycle events.
  Runtime Logs are separate from Audit Logs.
- **Idempotency Key**: A stable identifier that lets a side-effecting
  operation recognize and safely ignore a repeated request or event.
- **Dashboard Shell**: Reusable presentation structure around a page. It owns
  layout and navigation, not business behavior.
- **Mobile Presentation Mode**: An optional dashboard presentation mode that
  preserves the same routes, permissions, Domain App interfaces, and
  authoritative server state.
- **Production Deployment Contract**: The explicit agreement for process roles,
  external infrastructure, configuration, health evidence, and release order.

## Architectural facts

### Application ownership

The application map is:

| App | Ownership | Public boundary |
| --- | --- | --- |
| `core` | Users, roles, permissions, organization settings, identity, and RBAC | Public models, selectors, and services used by adapters |
| `platform_runtime` | Tasks, webhooks, realtime events, and Runtime Logs | `tasks`, `webhooks`, `realtime`, and `maintenance` |
| `dashboard` | Session-authenticated server-rendered UI | Views, forms, selectors, and service calls |
| `api` | Optional external REST/JWT adapter | Serializers, viewsets, and adapter contracts |
| `example` | Replaceable reference Domain App and Item CRUD | Its own selectors, services, forms, and templates |

Cross-domain imports are default-deny. Apps consume explicitly documented
public interfaces and must not import another app's private models, views,
forms, admin modules, signal wiring, or helpers. Workspace, Data, and Agent
apps are intentionally absent.

### Presentation and request authority

- Django Templates are the primary rendering boundary.
- HTMX handles server requests, mutations, filtering, pagination, and partial
  refreshes.
- Alpine.js handles local UI state such as menus, tabs, modals, toggles, and
  transitions.
- TailwindCSS semantic tokens define the presentation vocabulary.
- Django remains authoritative for authentication, authorization, validation,
  business state, database writes, and audit.
- Hidden controls, browser state, and localStorage are never security
  boundaries.

### Domain and data boundaries

Domain Apps own cohesive business concepts. Reads belong in selectors; writes,
invariants, transactions, and state transitions belong in services. Forms and
serializers validate transport shape, while database constraints enforce
relational guarantees.

Database changes use atomic transactions. Competing state transitions may use
row locks. External calls and deferred side effects occur after commit through
`transaction.on_commit()`. Side-effecting operations use state guards or
stable idempotency keys. Safe delete is the default.

### Platform Runtime

Platform Runtime is backend-neutral infrastructure. Background tasks are small,
retry-aware, timeout-bounded, and idempotent. Webhooks are verified and
deduplicated before processing. Realtime notifications are best effort; the
HTTP/HTMX response remains authoritative. Audit Logs and Runtime Logs use
separate purposes, access rules, retention, and redaction.

The baseline does not require Celery, Django-Q, Redis, Channels, a scheduler,
or a managed observability product. Production enables an explicit adapter only
when the deployment needs that capability.

### Authentication and authorization

Dashboard authentication uses Django sessions. The optional API adapter uses
JWT when enabled. Both surfaces enforce the same RBAC and business rules by
delegating to public selectors and services.

Permission checks use active role assignments and permission union. Superusers
may bypass RBAC according to the applicable policy. Every state-changing
request must preserve authentication, authorization, CSRF protection, input
validation, and audit behavior.

### Presentation shells and components

The existing Dashboard Shell is the default. Mobile Presentation Mode is
optional and resolves by:

```text
forced role policy -> user preference -> organization default
```

A route without a mobile-specific layout falls back to the default shell.
Shared UI components use Django Template Partials and semantic Tailwind tokens.
They expose presentation parameters and contain no business logic, queries,
permissions, or database writes.

### Deployment boundary

Production uses an immutable runtime image and external PostgreSQL. The web
process is serve-only. A release runs the migration step once from the release
image before web processes are scaled. Worker, scheduler, realtime, TLS,
backup, alerting, and incident response are deployment responsibilities that
must be explicitly configured when enabled.

## Intentional non-goals

djaapp does not provide these capabilities in the baseline:

- shared SaaS tenancy or Workspace/multi-workspace routing;
- DataSource, Dataset, Artifact, connector, refresh, or data-platform domains;
- AgentRun, AgentStep, ToolCall, PydanticAI, agent queues, or agent runtime;
- a mandatory worker, broker, scheduler, Redis, Channels, or realtime
  provider;
- a mandatory managed backup, TLS ingress, alerting, or observability vendor.

## Decision records

Durable architectural decisions are recorded in [docs/adr/README.md](docs/adr/README.md).
The current public decision set covers the deployment model, frontend stack,
Domain App boundaries, optional API adapter, Platform Runtime, dashboard
shells/components, and production deployment contract.

## Context maintenance

Update this file when terminology, ownership, public boundaries, or intentional
scope changes. Update the relevant ADR and `docs/architecture/app-map.md` in
the same change when the architecture changes. Keep private client briefs,
project-management workflows, internal runbooks, and delivery evidence out of
this public context file.

## Open questions

- Should role hierarchy levels affect permission decisions, or remain metadata
  for ordering and display? Current permission checks use permission union and
  do not compare role levels.
