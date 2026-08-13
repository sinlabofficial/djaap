# djaapp

djaapp is a production-oriented Django full-stack webapp starterkit for one
organization per deployment.

It provides a server-rendered dashboard foundation with Django Templates,
HTMX, Alpine.js, TailwindCSS, PostgreSQL, Docker, authentication, RBAC,
audit logging, optional REST integration, and a replaceable Domain App
example.

## What djaapp provides

- Django Templates as the primary presentation boundary.
- HTMX for server-backed interactions and partial updates.
- Alpine.js for local browser state and interaction behavior.
- TailwindCSS with semantic design tokens.
- Session-authenticated dashboard.
- Multi-identifier authentication with Users, Roles, Permissions, and RBAC.
- Singleton organization settings and audit logging.
- Service/selector boundaries for Domain App business logic.
- Optional REST API with JWT authentication.
- Docker Compose development environment with PostgreSQL and Tailwind watch.
- Production image, migration, smoke-test, and release-verification contracts.
- Documentation and AI-agent workflows for spec-driven delivery.

The starterkit is intentionally single-organization. Workspace or
multi-workspace tenancy, data-platform features, and agent-runtime features
are outside the baseline scope. Start a fresh installation for a client
project; legacy databases containing removed platform models are not supported
migration inputs.

## Architecture at a glance

    Browser / mobile client / integration
              |
              +--> /dashboard/ -- session auth --> dashboard adapter
              |                                    |
              |                                    +--> core public interfaces
              |                                    +--> Domain App interfaces
              |
              +--> /api/ ------ JWT optional ----> API adapter
              |                                    |
              |                                    +--> core / Domain App interfaces
              |
              +--> /webhooks/ - signature -------> platform runtime
                                                   |
                                  tasks / webhooks / realtime / runtime logs

The dashboard is the primary application interface. The API is an optional
adapter for external integrations or clients such as mobile applications.
Django remains authoritative for authentication, authorization, validation,
business state, and database writes.

| Concern | djaapp default |
| --- | --- |
| Internal UI | Django Templates and session authentication |
| Server interactions | HTMX |
| Local UI state | Alpine.js |
| Styling | TailwindCSS |
| Database | PostgreSQL 16 |
| Business reads | Selectors |
| Business writes | Services |
| External API | Optional REST/JWT adapter |
| Deployment | Docker runtime image and external PostgreSQL |
| Background capability | Explicit Django Tasks adapter when enabled |

## Domain App architecture

A Domain App owns one cohesive business concept and its public collaboration
interface.

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

Add task, webhook, API, or contract modules only when the capability exists.

The architecture rules are:

- selectors contain read-oriented queries;
- services contain business writes, invariants, and transactions;
- views, forms, serializers, and templates are adapters;
- cross-domain dependencies are default-deny;
- consumers use public selectors and services;
- permission is enforced server-side;
- safe delete is the default deletion model;
- side effects run after commit;
- Domain Apps do not import another app's private models, views, forms, or
  helpers.

The replaceable example Domain App demonstrates this structure.

## Requirements

- Python 3.14
- uv
- Node.js 22
- PostgreSQL 16, or Docker Compose
- Just command runner
- Docker Engine and Docker Compose for container development

## Quick start

Clone the repository and initialize the development environment:

    git clone <repository-url>
    cd <repository-directory>
    just init
    just create-test-user
    just run-local

Open:

    http://127.0.0.1:8000/dashboard/login/

For a Docker-based development environment:

    just init
    just run

The Docker development stack starts PostgreSQL, Django, and Tailwind watch
mode. Redis, Celery, and a scheduler are not required by the baseline.

For Tailwind watch mode outside the full Docker stack:

    just tailwind-watch

## Optional REST API

The REST API is an adapter, not the primary application interface. Add it only
for an identified external integration or client.

Install the optional API dependencies:

    uv sync --extra api --locked

API adapters must reuse public selectors and services and preserve the same
authentication, authorization, validation, and audit rules as the dashboard.

## Project layout

    backend/
      apps/
        api/              optional REST and JWT adapter
        core/             identity, RBAC, organization settings
        dashboard/        session-authenticated dashboard
        example/          replaceable Domain App reference
        platform_runtime/ generic tasks, webhooks, realtime, runtime logs
      config/             Django settings and environment configuration
      tests/              pytest suite
    frontend/             dashboard templates and frontend layout
    ui/                   Tailwind entry point and design tokens
    docker/               Dockerfile and startup/release scripts
    docs/                 architecture, guides, ADRs, and references
    .scratch/             local/private project management files; ignored by Git

## Daily commands

    just init                 Install and initialize dependencies
    just run-local            Run local Django development server
    just run                  Run Docker Compose development stack
    just verify               Run the standard verification gate
    just test-fast            Run the fast test suite
    just test-integration     Run integration tests
    just tailwind-build      Build production CSS
    just tailwind-watch      Watch Tailwind sources
    just runtime-image       Build the runtime Docker image
    just prod-config         Validate production-shaped configuration
    just check-deploy        Validate deployment readiness
    just prod-build          Build the production image
    just deploy-migrate      Run release migrations once
    just deploy              Start the production Compose service
    just parity-check        Verify toolchain/documentation parity
    just clean               Remove generated local artifacts

Read docs/toolchain-and-commands.md for the authoritative command and version
contract.

## Key URLs

| URL | Purpose |
| --- | --- |
| /dashboard/login/ | Session login |
| /dashboard/ | Internal dashboard |
| /api/health/ | Optional API health endpoint |
| /api/docs/swagger/ | Optional OpenAPI UI |
| /api/docs/redoc/ | Optional read-only OpenAPI UI |
| /api/docs/schema/ | Optional OpenAPI schema |
| /admin/ | Django administration |

The API documentation URLs exist only when the optional API capability is
installed and enabled.

## Environment configuration

Copy the appropriate example file:

    cp .env.example .env

Docker development uses backend/.env.example when applicable. Configure at
least the following values for production:

    DEBUG=False
    SECRET_KEY=<unique-random-secret>
    ALLOWED_HOSTS=app.example.com
    DATABASE_URL=postgres://<user>:<password>@<host>:5432/<database>
    DATABASE_SSL_REQUIRE=True
    CSRF_TRUSTED_ORIGINS=https://app.example.com

Use a real secret and an external production PostgreSQL database. Never commit
.env files, passwords, provider keys, tokens, or private data.

## Production deployment

The production reference uses an external PostgreSQL database and a serve-only
web startup process. It does not run migrations automatically on every web
startup.

The release flow is:

    just check-deploy
    just prod-build
    just deploy-migrate
    just deploy


## Contributing

Use a focused vertical slice and keep pull requests reviewable. Before opening
a pull request:

    just verify
    git diff --check

Read CONTRIBUTING.md, AGENTS.md, and the relevant project-management or
development playbook.

## License

djaapp is released under the MIT License. See LICENSE.
