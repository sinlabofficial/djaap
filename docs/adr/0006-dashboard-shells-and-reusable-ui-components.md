# ADR-0006: Dashboard Shells and Reusable UI Components

## Status

Accepted

## Date

2026-08-14

## Context

The starterkit needs a stable default dashboard while allowing an optional
mobile presentation mode. Shared UI patterns should be reusable without
creating a second business layer or coupling components to domain data.

## Decision

The existing Dashboard Shell remains the default presentation. Mobile
Presentation Mode is optional and uses the same routes, Domain App selectors,
services, permissions, forms, and authoritative server state.

Presentation mode is resolved in this order:

```text
forced role policy -> user preference -> organization default
```

Shared UI Components use Django Template Partials and semantic TailwindCSS
tokens. Components expose presentation parameters such as variant, size,
disabled, error, and loading states. They do not own business logic, queries,
permissions, or database writes.

## Consequences

- Existing dashboard behavior remains stable while mobile presentation can be
  introduced incrementally.
- Domain Apps do not need duplicate mobile routes or business workflows.
- UI components remain testable presentation units with a narrow contract.
- The active token palette remains the implementation source of truth; design
  references must not override token definitions.

## Rejected alternatives

- A separate `/mobile/` application was rejected because it duplicates routing,
  authorization, and business behavior.
- A SPA or global frontend store was rejected because Django Templates, HTMX,
  and Alpine.js satisfy the existing presentation boundary.
- An automatic plugin registry for navigation was rejected for the foundation;
  navigation remains an explicit public contract.
