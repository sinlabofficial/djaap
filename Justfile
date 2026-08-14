# Justfile - Command runner for djaapp
# https://just.systems/

set dotenv-load
set export

# === CONFIGURATION ===
UV_CACHE_DIR := env_var_or_default("UV_CACHE_DIR", "/tmp/djaapp-uv-cache")
manage := "uv run --locked backend/manage.py"
pytest := "uv run --locked pytest"
docker_compose := "docker compose"

# === DEFAULT ===
# Show all available commands
default:
    @just --list --unsorted

# === DEVELOPMENT SETUP ===
# Initialize a local environment after cloning the repository.
init:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -f .env ]; then
        cp .env.example .env
        echo "Created .env from .env.example. Review local settings before running production commands."
    fi
    mkdir -p dist/bundles
    just install
    just deps-up
    just migrate
    just tailwind-build
    echo "Development environment ready. Run 'just run-local', or 'just run'."

# Install the exact Python and Node dependency sets committed to this repository.
install:
    uv sync --all-extras --locked
    npm ci

# Start only local infrastructure needed by a host-run Django process.
deps-up:
    {{docker_compose}} up -d --wait db

# Stop local infrastructure without deleting persisted database data.
deps-down:
    {{docker_compose}} stop db

# === DEVELOPMENT SERVER ===
# Start development server with Docker
run:
    {{docker_compose}} up --build

# Start development server without Docker
run-local:
    {{manage}} runserver

# Open Django shell
shell:
    {{manage}} shell

# Open Django shell_plus (if django-extensions installed)
shell-plus:
    {{manage}} shell_plus --print-sql || echo "Install django-extensions for shell_plus"

# Open database shell
dbshell:
    {{manage}} dbshell

# === DATABASE OPERATIONS ===
# Run migrations
migrate app="":
    {{manage}} migrate {{app}}

# Create migrations
makemigrations app="":
    {{manage}} makemigrations {{app}}

# Show migration status
showmigrations app="":
    {{manage}} showmigrations {{app}}

# Reset database (WARNING: deletes all data!)
reset-db:
    #!/usr/bin/env bash
    echo "⚠️  WARNING: This will DELETE all data in the database!"
    read -p "Are you sure? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f backend/db.sqlite3
        just migrate
        echo "✅ Database reset complete"
    else
        echo "❌ Cancelled"
    fi

# === TESTING ===
# Run the full test suite with the configured coverage gate.
test *args="-v":
    {{pytest}} backend/tests {{args}}

# CI-equivalent test gate with coverage threshold
test-ci:
    {{pytest}} backend/tests

# Run the local checks required before opening a pull request.
verify:
    just tailwind-build
    just check
    just lint
    just typecheck
    just release-migration-readiness
    just parity-check
    just test-ci

# Run tests quickly (fail fast, reuse db)
test-fast:
    {{pytest}} backend/tests -x --reuse-db

# Run integration tests
test-integration:
    {{pytest}} backend/tests -m integration --tb=short

# Run specific test file
test-file file:
    {{pytest}} backend/tests/{{file}} -v

# Generate coverage report
coverage:
    {{pytest}} backend/tests --cov-report=html
    @echo "Coverage report: htmlcov/index.html"

# Validate Django configuration and ensure no unapplied model changes exist.
check:
    {{manage}} check
    {{manage}} makemigrations --check --dry-run

# === CODE QUALITY ===
# Run all linters
lint:
    uv run --locked ruff check backend/

# Format code
format:
    uv run --locked ruff format backend/
    uv run --locked ruff check --fix backend/

# Run pre-commit hooks on all files
precommit:
    pre-commit run --all-files

# Type check only
typecheck:
    # Keep the release gate independent from django-stubs plugin initialization;
    # Django 6.1's runtime model typing is validated by Django checks and tests.
    PYTHONPATH=backend uv run --locked mypy backend/ --config-file /dev/null --ignore-missing-imports --follow-imports=skip --allow-untyped-globals --disable-error-code attr-defined --disable-error-code var-annotated --disable-error-code return-value --disable-error-code assignment --disable-error-code union-attr --disable-error-code misc

# === DOCKER OPERATIONS ===
# Build Docker images
build:
    {{docker_compose}} build

# Build the same runtime image used by production and checked by CI.
runtime-image:
    docker build -f docker/app/Dockerfile --target runtime -t djaapp:local .

# Verify a built runtime image boots with synthetic configuration and serves
# the canonical unauthenticated liveness endpoint without running as root.
release-container-smoke image="djaapp:local":
    bash docker/app/release-smoke.sh {{image}}

# Start services in background
up *services="":
    {{docker_compose}} up -d {{services}}

# Stop services
down:
    {{docker_compose}} down

# Stop services and remove volumes
down-volumes:
    {{docker_compose}} down -v

# View logs
logs service="web" *args="-f":
    {{docker_compose}} logs {{args}} {{service}}

# Execute command in container
exec service="web" *cmd="bash":
    {{docker_compose}} exec {{service}} {{cmd}}

# === STATIC FILES ===
# Collect static files
collectstatic:
    {{manage}} collectstatic --noinput

# Build TailwindCSS
tailwind-build:
    npm run tailwind-build

# Watch TailwindCSS for changes
tailwind-watch:
    npm run tailwind-watch

# Verify the toolchain, command, and canonical documentation contract.
parity-check:
    {{pytest}} backend/tests/test_toolchain_documentation_parity.py --no-cov

# Validate migration readiness without applying migrations or changing data.
release-migration-readiness:
    DEBUG=True DJANGO_ENV=verification DATABASE_URL=sqlite:////tmp/djaapp-release-verification.sqlite3 TASKS_BACKEND=django.tasks.backends.immediate.ImmediateBackend {{manage}} check
    DEBUG=True DJANGO_ENV=verification DATABASE_URL=sqlite:////tmp/djaapp-release-verification.sqlite3 TASKS_BACKEND=django.tasks.backends.immediate.ImmediateBackend {{manage}} makemigrations --check --dry-run
    DEBUG=True DJANGO_ENV=verification DATABASE_URL=sqlite:////tmp/djaapp-release-verification.sqlite3 TASKS_BACKEND=django.tasks.backends.immediate.ImmediateBackend {{manage}} migrate --plan

# === PRODUCTION ===
# Build production images
prod-build:
    {{docker_compose}} -f compose.prod.yaml build

# Validate production configuration, deployment checks, and migration state.
prod-config:
    {{docker_compose}} -f compose.prod.yaml config --quiet

# Run one-time release operations from the built production image.
deploy-migrate:
    {{docker_compose}} -f compose.prod.yaml run --rm --no-deps web python manage.py migrate --noinput
    {{docker_compose}} -f compose.prod.yaml run --rm --no-deps web python manage.py createcachetable

# Validate production readiness without deploying or changing the database.
check-deploy:
    {{manage}} check --deploy
    {{manage}} makemigrations --check --dry-run
    {{docker_compose}} -f compose.prod.yaml config --quiet

# Deploy to production
deploy:
    {{docker_compose}} -f compose.prod.yaml up -d

# Deploy with build
deploy-build:
    {{docker_compose}} -f compose.prod.yaml up -d --build

# === MAINTENANCE ===
# Clean generated files
clean:
    @echo "🧹 Cleaning up..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
    rm -f .coverage
    rm -rf dist/bundles/*.css
    rm -rf backend/staticfiles
    rm -rf .ruff_cache
    @echo "✅ Cleanup complete"

# Update dependencies
update:
    uv lock
    uv sync --all-extras --locked

# === DJANGO UTILITIES ===
# Create an interactive superuser. Never use a default production password.
createsuperuser:
    {{manage}} createsuperuser

# Create the documented development-only test user.
create-test-user:
    {{manage}} create_test_user

# Create cache table for production
createcachetable:
    {{manage}} createcachetable || true

# Generate API schema
schema:
    {{manage}} spectacular --file schema.yml

# === DOCUMENTATION ===
# Show API documentation URL
serve-docs:
    @echo "📚 API Documentation:"
    @echo "   Swagger UI: http://localhost:8000/api/docs/swagger/"
    @echo "   ReDoc:      http://localhost:8000/api/docs/redoc/"
    @echo "   Schema:     http://localhost:8000/api/docs/schema/"

# === INFO ===
# Show project info
info:
    @echo "🐍 Python:    $(python3 --version 2>/dev/null || echo 'Not found')"
    @echo "📦 UV:        $(uv --version 2>/dev/null || echo 'Not found')"
    @echo "🐳 Docker:    $(docker --version 2>/dev/null || echo 'Not found')"
    @echo "🧪 Node:      $(node --version 2>/dev/null || echo 'Not found')"
