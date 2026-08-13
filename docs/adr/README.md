# Architecture Decision Records

This directory is the decision log for the public djaapp starterkit. It
records architectural choices that affect application boundaries, technology
contracts, deployment shape, or long-term maintenance.

ADRs answer **why the starterkit is shaped this way**. They are not feature
specifications, implementation tickets, deployment runbooks, or private client
project documentation.

## Decision index

| ADR | Title | Status | Date |
| --- | --- | --- | --- |
| [0001](0001-single-organization-deployment.md) | Single-organization deployment model | Accepted | 2026-08-14 |
| [0002](0002-dashboard-frontend-stack.md) | Server-rendered dashboard frontend stack | Accepted | 2026-08-14 |
| [0003](0003-domain-app-boundaries.md) | Domain App boundaries and public service interfaces | Accepted | 2026-08-14 |
| [0004](0004-optional-api-adapter.md) | Optional REST API adapter | Accepted | 2026-08-14 |
| [0005](0005-platform-runtime-reliability-and-logs.md) | Platform Runtime reliability and operational logs | Accepted | 2026-08-14 |
| [0006](0006-dashboard-shells-and-reusable-ui-components.md) | Dashboard shells and reusable UI components | Accepted | 2026-08-14 |
| [0007](0007-production-deployment-contract.md) | Explicit production deployment contract | Accepted | 2026-08-14 |

## Statuses

| Status | Meaning |
| --- | --- |
| Proposed | A decision under review; it is not an implementation constraint yet. |
| Accepted | The decision is approved and is an active architecture constraint. |
| Superseded | A later ADR replaces this decision; the original remains for historical context. |
| Rejected | The alternatives were considered and explicitly not selected. |

## When an ADR is needed

Create or update an ADR when a decision:

- changes a system boundary or ownership rule;
- introduces, removes, or makes a dependency mandatory;
- changes the dashboard, API, database, runtime, or deployment contract;
- creates a rule that future Domain Apps must follow; or
- has meaningful consequences that would otherwise be rediscovered later.

Routine bug fixes, isolated refactors, visual changes, and ordinary feature
work do not need an ADR unless they change one of those contracts.

## ADR format

Every ADR uses the following sections:

1. `Status`
2. `Date`
3. `Context`
4. `Decision`
5. `Consequences`
6. `Rejected alternatives`

Add `References` when a decision depends on a specific source, code boundary,
or related ADR.

## Lifecycle rules

- Use the next available four-digit number in filename order.
- Use a short, descriptive, kebab-case filename after the number.
- Keep accepted ADRs historically stable; do not silently rewrite their
  decision because implementation details changed.
- When an accepted decision changes, create a new ADR and mark the old one
  `Superseded` with a link to its replacement.
- Update this index whenever an ADR is added, renamed, or superseded.
- Keep implementation details in code, tests, and the relevant technical
  documentation. Link to them when useful, but do not duplicate them here.

## Relationship to the starterkit

The ADRs are read together with:

- `CONTEXT.md` for product vocabulary and stable architectural facts;
- `docs/architecture/app-map.md` for application ownership and public
  interfaces; and
- `docs/code-conventions.md` for naming, implementation, and testing rules.

When those documents appear to disagree, treat the accepted ADR as the record
of the architectural decision and update the affected implementation or
documentation contract in the same change.
