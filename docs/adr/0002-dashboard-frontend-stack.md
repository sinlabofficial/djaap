# ADR-0002: Server-Rendered Dashboard Frontend Stack

## Status

Accepted

## Date

2026-08-14

## Context

djaapp targets internal business webapps that benefit from server-authoritative
HTML, progressive enhancement, simple deployment, and low client-side state
complexity. The starterkit must support responsive dashboard interactions
without requiring a frontend build framework for business behavior.

## Decision

The dashboard uses Django Templates as the primary rendering boundary, HTMX for
server-backed requests and partial updates, Alpine.js for local browser state,
and TailwindCSS with semantic design tokens for styling.

Django remains authoritative for authentication, authorization, validation,
business state, database writes, and audit. HTMX may request full pages or
fragments, but it must not become a second source of business rules. Alpine.js
may manage local UI state such as menus, tabs, modals, and toggles, but it must
not enforce permissions or persist business state independently.

## Consequences

- Pages are progressively enhanced and remain understandable as Django flows.
- Server-side tests can cover business behavior without a browser runtime.
- Interactive components need explicit full-page and fragment response
  contracts.
- Frontend code must preserve CSRF, keyboard access, focus, ARIA, and mobile
  behavior.

## Rejected alternatives

- A SPA as the default was rejected because it adds a second application state
  model and a larger deployment/toolchain surface.
- Direct client-side CRUD APIs were rejected because dashboard writes should
  use the same server-side authorization and service boundaries.
