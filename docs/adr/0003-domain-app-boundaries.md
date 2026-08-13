# ADR-0003: Domain App Boundaries and Public Service Interfaces

## Status

Accepted

## Date

2026-08-14

## Context

Starterkits often become difficult to extend when views, models, and utility
modules are imported across unrelated concerns. djaapp needs a repeatable
structure that lets client projects add business capabilities without creating
an accidental shared monolith.

## Decision

Each Domain App owns one cohesive business concept: its models, invariants,
permissions, navigation, selectors, services, forms, views, templates, and
tests. Reads belong in public selectors. Business writes, transactions, and
state transitions belong in public services. Views, forms, serializers, and
templates are adapters around those interfaces.

Cross-domain imports are default-deny. A Domain App may consume another app
only through an explicitly documented public selector, service, or contract.
Each cross-domain workflow has one Workflow Owner. Import-boundary tests must
remain aligned with the application map.

## Consequences

- Business rules have a predictable location and can be reused by dashboard
  and optional API adapters.
- Domain Apps can evolve independently when their public interfaces remain
  stable.
- Cross-domain work requires explicit ownership and contract tests.
- Generic repositories, speculative utility layers, and private model imports
  are discouraged.

## Rejected alternatives

- Allowing all apps to import models directly was rejected because it hides
  ownership and makes changes unsafe.
- A mandatory generic repository layer was rejected because selectors and
  services already provide the required boundaries.
