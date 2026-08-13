from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_production_compose_uses_external_database_contract():
    compose = yaml.safe_load((ROOT / "compose.prod.yaml").read_text())

    assert set(compose["services"]) == {"web"}
    assert "postgres" not in str(compose).lower()
    assert "volumes" not in compose
    assert "DATABASE_URL" in compose["services"]["web"]["environment"]


def test_production_startup_is_serve_only():
    startup = (ROOT / "docker/app/start-prod.sh").read_text()

    assert "manage.py migrate" not in startup
    assert "manage.py collectstatic" not in startup
    assert "manage.py createcachetable" not in startup
    assert "exec gunicorn" in startup


def test_justfile_exposes_release_operations_and_full_deploy_check():
    justfile = (ROOT / "Justfile").read_text()

    assert "deploy-migrate:" in justfile
    assert "{{docker_compose}} -f compose.prod.yaml run --rm --no-deps web python manage.py migrate --noinput" in justfile
    assert "{{docker_compose}} -f compose.prod.yaml run --rm --no-deps web python manage.py createcachetable" in justfile
    assert "createcachetable || true" not in justfile[justfile.index("deploy-migrate:") : justfile.index("# Validate production readiness")]
    check_deploy = justfile[justfile.index("check-deploy:") :]
    assert "{{manage}} check --deploy" in check_deploy
    assert "{{manage}} makemigrations --check --dry-run" in check_deploy
    assert "{{docker_compose}} -f compose.prod.yaml config --quiet" in check_deploy


def test_production_toolchain_uses_node_22_everywhere():
    dockerfile = (ROOT / "docker/app/Dockerfile").read_text()
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    readme = (ROOT / "README.md").read_text()

    assert "FROM node:22-alpine" in dockerfile
    assert 'node-version: "22"' in workflow
    assert "Node.js 22" in readme


def test_agents_guide_exposes_public_architecture_contract_only():
    agents = (ROOT / "AGENTS.md").read_text()

    assert "docs/adr/0001-dashboard-frontend-stack.md" not in agents
    assert "docs/architecture/app-map.md" in agents
    assert "docs/adr/0006-single-organization-full-stack-webapp.md" not in agents
    assert "docs/platform-runtime-deployment.md" not in agents
    assert "docs/operations-runbook-and-observability.md" not in agents
    assert "docs/guides/project-management-for-djaapp.md" not in agents
