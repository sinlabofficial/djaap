# djaapp Agent Guide

> Document version: 3.0.0 | Last reviewed: 2026-08-14

This file is the operating contract for AI agents and developers working in the
djaapp repository. Read it before substantial work.

## Repository purpose

djaapp is a single-organization Django full-stack webapp starterkit. Its
primary stack is Django Templates, HTMX, Alpine.js, TailwindCSS, PostgreSQL,
Docker, and optional REST/JWT adapters.

The starterkit intentionally does not provide:

- Workspace or multi-workspace tenancy;
- data-platform capabilities such as DataSource, Dataset, Artifact, or
  connector workflows;
- an agent runtime, AgentRun, ToolCall, PydanticAI, Celery, or agent queue;
- a mandatory worker, scheduler, broker, Redis, or realtime provider.

Keep the baseline generic, installable, and suitable for a fresh client project.

## Source-of-truth documents

Read only the documents relevant to the task, but always start with:

1. AGENTS.md;
2. CONTEXT.md;
3. the relevant ADR in docs/adr/;
4. docs/architecture/app-map.md;
5. docs/code-conventions.md;
6. the relevant guide and adjacent tests.

Use the documents as follows:

| Need | Source |
| --- | --- |
| Product vocabulary and stable domain facts | CONTEXT.md |
| Current architecture and app ownership | docs/architecture/ |
| Naming, structure, Do/Don't, and code style | docs/code-conventions.md |
| Relevant implementation documentation | The closest public guide or module documentation |

The public ADR index is [docs/adr/README.md](docs/adr/README.md). It records
the durable decisions for this starterkit. Do not copy private client
workflow, delivery, or operations documentation into this file.

Use only repository documentation that is relevant to the current task. Keep
private project-management workflows, client briefs, internal runbooks, and
delivery evidence outside this public agent contract.

## Scope and privacy

Keep private project-management workflows, client briefs, internal runbooks,
delivery evidence, credentials, production secrets, and raw incident evidence
outside this public agent contract and outside tracked documentation.

## Architecture contract

- The dashboard is server-rendered Django Templates with session auth.
- HTMX owns server-backed interaction and partial updates.
- Alpine.js owns local browser state only.
- TailwindCSS owns styling and semantic design tokens.
- The dashboard is the primary application interface.
- REST/JWT is an optional adapter for external integrations or mobile clients.
- One installation serves one organization; there is no Workspace tenancy.
- Server-side Django code remains authoritative for validation, authorization,
  business state, database writes, and audit.
- Superusers or authorized staff may mutate according to the applicable RBAC
  policy; hidden UI controls are never a security boundary.
- `core` owns global identity, RBAC, and organization settings.
- `dashboard` owns the primary server-rendered application interface.
- `api` is an optional adapter for external integrations and mobile clients.
- `platform_runtime` owns generic task, webhook, realtime, and runtime-log
  contracts; it does not own Domain App business semantics.
- `example` is a replaceable Domain App reference, not a shared utility app.
- New architecture-affecting decisions must be recorded as a numbered ADR in
  `docs/adr/` and added to its README index.

## Domain App contract

A Domain App owns one cohesive business concept, including its models,
invariants, permissions, navigation, selectors, services, templates, and tests.

A normal Domain App structure is:

    backend/apps/<domain>/
    ├── AGENTS.md
    ├── apps.py
    ├── models.py
    ├── selectors.py
    ├── services.py
    ├── forms.py
    ├── views.py
    ├── urls.py
    ├── migrations/
    └── tests/

Add tasks, webhooks, API adapters, or contracts only when the capability
actually exists. Use backend/apps/example/AGENTS.md as the reference local
Domain App contract when no more specific contract exists.

Rules:

- reads belong in selectors.py;
- business writes and transactions belong in services.py;
- views, forms, serializers, and templates are adapters;
- cross-domain imports are default-deny;
- use public selectors to read another Domain App;
- use public services to write to another Domain App;
- never import another Domain App's private models, views, forms, admin,
  tasks, signals, or helpers;
- assign one Workflow Owner to each cross-domain workflow;
- keep backend/tests/architecture/test_import_boundaries.py aligned with the
  App Map.

Do not create generic repositories, speculative utils.py modules, or framework
layers when an existing public boundary is sufficient.

## Data, transaction, and side-effect rules

- Use forms or serializers for transport/input validation.
- Use services for business validation, permission, invariant, and state
  transition.
- Use model/database constraints for relational guarantees.
- Use transaction.atomic() for changes that must be atomic.
- Use select_for_update() for competing state transitions when required.
- Keep transactions short and do not make long external network calls inside
  them.
- Use transaction.on_commit() for tasks, realtime events, email, or external
  side effects.
- Use unique constraints, state guards, or idempotency keys for repeatable
  side-effecting commands.
- Safe delete is the default; do not introduce hard delete without an explicit
  product decision.
- Keep Audit Log separate from Runtime Log.
- Redact credentials, secrets, and sensitive payloads from logs and audit.

## Frontend boundaries

For dashboard UI:

- render structure and initial data with Django Templates;
- use HTMX for server requests, mutations, filtering, pagination, and
  authoritative partial refresh;
- use Alpine.js for dropdowns, modal visibility, tabs, toggles, transitions,
  local preferences, and other local state;
- keep business decisions and permission enforcement on the server;
- preserve CSRF and permission checks for every state-changing request;
- test full-page and HTMX fragment responses separately where applicable;
- verify keyboard, focus, ARIA, and mobile behavior for interactive components.

Do not introduce a SPA, global frontend store, or direct client-side CRUD API
without an explicit architecture decision.

## Security and privacy

- Never commit secrets, credentials, private keys, or production data.
- Do not weaken RBAC or validation to make a UI flow easier.
- Treat browser state and localStorage as untrusted and non-secret.
- Do not use hidden UI controls as authorization.
- Use safe redaction for audit, runtime, webhook, and realtime data.
- Do not run production or destructive commands as part of ordinary local
  implementation.
- Escalate credential, security, legal, destructive, and production decisions
  to a human owner.

## Engineering workflow

1. Classify the task as feature, fix, refactor, security, performance,
   documentation, dependency, or chore.
2. Read the source-of-truth documents and inspect adjacent implementation/tests.
3. For larger work, create or update a local spec and ordered tickets.
4. Confirm ownership, public interfaces, dependencies, acceptance criteria, and
   non-goals before coding.
5. Use TDD for behavior changes: failing test, minimal implementation, refactor.
6. Prefer existing seams: selector, service, dashboard HTMX route, or optional
   API adapter.
7. Keep the diff small and scoped. Do not revert unrelated worktree changes.
8. Update code, tests, documentation, ADR, App Map, or deployment contract when
   the public behavior changes.
9. Run focused verification first, then the relevant full gate.
10. Record evidence, not merely a statement that the work is complete.

## Verification

Use the repository's Just recipes when Git and dependencies are initialized:

    just test-fast
    just verify
    just parity-check
    just check-deploy
    just prod-build
    just release-migration-readiness

For focused local checks, use the virtual environment when uv cannot resolve
build dependencies:

    ./.venv/bin/ruff check backend
    ./.venv/bin/pytest backend/tests
    ./.venv/bin/python backend/manage.py check
    ./.venv/bin/python backend/manage.py makemigrations --check --dry-run

For dashboard changes, verify:

- session authentication;
- global RBAC and permission-filtered actions;
- public selector/service usage;
- full-page and HTMX response behavior;
- Alpine local state;
- mobile and keyboard behavior;
- single-organization operation without Workspace context.

Do not claim completion from command invocation alone. Read the output and report
passed checks, failed checks, checks not run, and remaining risk.

## Production boundary

- Build and verify an immutable runtime image.
- Keep web startup serve-only; do not run migrations on every web instance.
- Run deploy-migrate once before scaling web processes.
- Use external production PostgreSQL.
- Enable worker, scheduler, realtime, TLS, backup, alerting, and incident
  response only when the deployment contract explicitly configures them.
- Distinguish repository-safe evidence from staging/production evidence.
- Follow the deployment environment's approved release, operations, and
  recovery contracts for production work.

## Constraints

- Preserve unrelated user changes in a dirty worktree.
- Use apply_patch for manual file edits.
- Prefer ASCII in source and documentation unless the existing document requires
  otherwise.
- Do not add an external dependency when existing Django/HTMX/Alpine/Tailwind
  boundaries satisfy the requirement.
- Do not publish private project-management data or deployment evidence.
- Do not add private or client-specific documentation references to this file.
