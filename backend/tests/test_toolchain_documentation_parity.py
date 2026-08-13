import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JUSTFILE = ROOT / "Justfile"
CANONICAL_DOCS = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "docs" / "release-gate.md",
    ROOT / "docs" / "platform-runtime-deployment.md",
    ROOT / "docs" / "operations-runbook-and-observability.md",
    ROOT / "docs" / "toolchain-and-commands.md",
]


def test_node_22_is_declared_across_toolchain_surfaces():
    package = (ROOT / "package.json").read_text()
    package_lock = (ROOT / "package-lock.json").read_text()
    compose = (ROOT / "compose.yaml").read_text()
    dockerfile = (ROOT / "docker/app/Dockerfile").read_text()
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert '"node": ">=22 <23"' in package
    assert '"node": ">=22 <23"' in package_lock
    assert "node:22-alpine" in compose
    assert "node:22-alpine" in dockerfile
    assert 'node-version: "22"' in workflow
    for path in CANONICAL_DOCS:
        docs = path.read_text()
        assert "22 or newer" not in docs, path
        if "Node" in docs or "node" in docs:
            assert "Node 22" in docs or "Node.js 22" in docs or "Node.js | 22" in docs, path
        assert "node:20" not in docs, path
    assert "Node.js | 22" in (ROOT / "docs/toolchain-and-commands.md").read_text()
    assert "node:20" not in compose + dockerfile + workflow


def test_python_and_database_versions_are_consistent():
    python_version = (ROOT / ".python-version").read_text().strip()
    pyproject = (ROOT / "pyproject.toml").read_text()
    dockerfile = (ROOT / "docker/app/Dockerfile").read_text()
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    compose = (ROOT / "compose.yaml").read_text()
    contract = (ROOT / "docs/toolchain-and-commands.md").read_text()

    assert python_version == "3.14"
    assert "requires-python = \">=3.14\"" in pyproject
    assert "FROM python:3.14-slim" in dockerfile
    assert 'python-version: "3.14"' in workflow
    assert "PostgreSQL | 16" in contract
    assert "postgres:16-alpine" in compose


def test_documented_commands_exist_as_just_recipes():
    justfile = JUSTFILE.read_text()
    recipes = set(re.findall(r"^([a-z][a-z0-9-]*)(?:\s+.*)?\s*:$", justfile, re.MULTILINE))
    documented = set()
    for path in CANONICAL_DOCS:
        documented.update(re.findall(r"\bjust ([a-z][a-z0-9-]*)\b", path.read_text()))

    assert documented <= recipes


def test_canonical_docs_classify_external_operations_and_release_order():
    contract = (ROOT / "docs/toolchain-and-commands.md").read_text()
    deployment = (ROOT / "docs/platform-runtime-deployment.md").read_text()

    assert "external task adapter required" in contract
    assert "deployment-platform responsibilities" in contract
    order = [
        "`just check-deploy`",
        "`just prod-build`",
        "`just deploy-migrate`",
        "start the web process",
        "run the unauthenticated web health probe",
        "monitor logs and error rates",
    ]
    positions = [deployment.index(item) for item in order]
    assert positions == sorted(positions)


def test_canonical_markdown_links_resolve_locally():
    markdown_files = [
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "CONTRIBUTING.md",
        *ROOT.glob("docs/**/*.md"),
    ]
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

    missing = []
    for path in markdown_files:
        for match in link_pattern.finditer(path.read_text()):
            target = match.group(1).split("#", 1)[0].strip("<>")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                missing.append(f"{path}: {target}")

    assert not missing, "Broken local Markdown links:\n" + "\n".join(missing)


def test_operations_runbook_covers_recovery_and_external_evidence_boundary():
    runbook = (ROOT / "docs/operations-runbook-and-observability.md").read_text()
    deployment = (ROOT / "docs/platform-runtime-deployment.md").read_text()

    required_sections = [
        "## Monitoring signals",
        "## Incident response",
        "## Backup and restore",
        "## Rollback",
        "## Recovery verification record",
    ]
    for section in required_sections:
        assert section in runbook
    for phrase in [
        "`GET /dashboard/login/`",
        "does not prove database",
        "write readiness",
        "production credentials",
        "isolated target",
        "irreversible or incompatible",
        "forward fix",
        "stabilization window",
        "external process",
        "redaction and retention",
    ]:
        assert phrase in runbook
    recovery_contract = runbook[runbook.index("## Backup and restore") :]
    backup_checkpoint = recovery_contract.index("backup checkpoint")
    deploy_migrate = recovery_contract.index("`just deploy-migrate`")
    assert backup_checkpoint < deploy_migrate
    recovery_checks = [
        "database connectivity",
        "migration consistency",
        "application boot",
        "unauthenticated health probe",
        "authorization",
        "stabilization window",
    ]
    recovery_positions = [recovery_contract.index(item) for item in recovery_checks]
    assert recovery_positions == sorted(recovery_positions)
    assert "backup checkpoint" in deployment
    assert "Operations Runbook and Observability Contract" in deployment


def test_release_gate_requires_operational_handoff_evidence():
    gate = (ROOT / "docs/release-gate.md").read_text()
    for phrase in [
        "backup checkpoint",
        "restore-drill",
        "rollback compatibility decision",
        "monitoring owner",
        "recovery verification record",
        "do not prove external worker liveness",
    ]:
        assert phrase in gate


def test_release_verification_contract_matches_runtime_surfaces():
    justfile = JUSTFILE.read_text()
    smoke = (ROOT / "docker/app/release-smoke.sh").read_text()
    dockerfile = (ROOT / "docker/app/Dockerfile").read_text()
    deployment = (ROOT / "docs/platform-runtime-deployment.md").read_text()
    runbook = (ROOT / "docs/operations-runbook-and-observability.md").read_text()
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    startup = (ROOT / "docker/app/start-prod.sh").read_text()

    for recipe in ["release-container-smoke", "release-migration-readiness"]:
        assert recipe in justfile
    assert "docker/app/release-smoke.sh" in justfile
    assert "migrate --plan" in justfile
    assert "makemigrations --check --dry-run" in justfile
    assert "DATABASE_URL=sqlite:////tmp/djaapp-release-verification.sqlite3" in justfile
    assert "DEBUG=False" in smoke
    assert "postgres:16-alpine" in smoke
    assert "DummyBackend" in smoke
    assert "--connect-timeout 1 --max-time 2" in smoke
    assert "docker logs --tail 100" in smoke
    assert "disposable PostgreSQL did not become ready" in smoke
    assert "database_diagnostics" in smoke
    assert "web_diagnostics" in smoke
    assert "GET /dashboard/login/" in runbook
    assert "/dashboard/login/" in smoke
    assert "/dashboard/login/" in dockerfile
    assert "exec gunicorn" in startup
    assert "release-container-smoke" in deployment
    assert "release-migration-readiness" in deployment
    assert "production credentials" in runbook
    assert "worker" in runbook
    assert "Smoke test production runtime image" in workflow
    assert "DATABASE_URL=sqlite:////tmp/djaapp-release-verification.sqlite3" in workflow
    verify = justfile[justfile.index("verify:") : justfile.index("# Run tests quickly")]
    release_order = [
        "just release-migration-readiness",
        "just parity-check",
        "just test-ci",
    ]
    positions = [verify.index(item) for item in release_order]
    assert positions == sorted(positions)
