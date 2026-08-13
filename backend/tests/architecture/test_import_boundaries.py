"""Lightweight import-boundary checks for domain Django apps.

Keep the policy intentionally small. When a new domain app is added, register
it here and document the same dependency in docs/architecture/app-map.md.
"""

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
APPS_ROOT = REPOSITORY_ROOT / "backend" / "apps"
DOMAIN_APPS = {"example"}
ALLOWED_DEPENDENCIES = {
    "example": {
        "core": {"models", "selectors"},
        "platform_runtime": {"tasks", "realtime", "webhooks", "maintenance"},
    },
}
def imported_app_modules(source: str) -> set[tuple[str, str]]:
    """Return absolute ``apps.<app>.<module>`` imports in *source*."""
    imports: set[tuple[str, str]] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        module = None
        if isinstance(node, ast.ImportFrom):
            module = node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("apps."):
                    parts = alias.name.split(".")
                    if len(parts) >= 3:
                        imports.add((parts[1], parts[2]))
        if module and module.startswith("apps."):
            parts = module.split(".")
            if len(parts) >= 3:
                imports.add((parts[1], parts[2]))
            elif len(parts) == 2 and isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.add((parts[1], alias.name))
    return imports


def is_allowed_cross_app_import(
    *,
    source_app: str,
    target_app: str,
    target_module: str,
    domain_apps: set[str] = DOMAIN_APPS,
) -> bool:
    """Apply the default-deny policy to one cross-app import."""
    if source_app == target_app:
        return True
    return target_module in ALLOWED_DEPENDENCIES.get(source_app, {}).get(
        target_app, set()
    )


def test_app_map_and_example_contract_exist():
    assert (REPOSITORY_ROOT / "docs" / "architecture" / "app-map.md").is_file()
    assert (APPS_ROOT / "example" / "AGENTS.md").is_file()


def test_domain_apps_only_use_declared_cross_app_imports():
    for app_name in DOMAIN_APPS:
        for source_file in (APPS_ROOT / app_name).rglob("*.py"):
            if "migrations" in source_file.parts:
                continue
            for target_app, target_module in imported_app_modules(
                source_file.read_text()
            ):
                assert is_allowed_cross_app_import(
                    source_app=app_name,
                    target_app=target_app,
                    target_module=target_module,
                ), (
                    f"{source_file.relative_to(REPOSITORY_ROOT)} imports "
                    f"apps.{target_app}.{target_module}; declare a platform "
                    "dependency or use a public domain interface."
                )


def test_direct_foreign_model_import_is_rejected():
    imported = imported_app_modules("from apps.inventory.models import Stock")
    target_app, target_module = next(iter(imported))

    assert not is_allowed_cross_app_import(
        source_app="orders",
        target_app=target_app,
        target_module=target_module,
        domain_apps={"orders", "inventory"},
    )


def test_domain_app_runtime_dependencies_are_public_only():
    for module in ALLOWED_DEPENDENCIES["example"]["platform_runtime"]:
        assert is_allowed_cross_app_import(
            source_app="example",
            target_app="platform_runtime",
            target_module=module,
            domain_apps=DOMAIN_APPS,
        )

    assert not is_allowed_cross_app_import(
        source_app="example",
        target_app="platform_runtime",
        target_module="observability",
        domain_apps=DOMAIN_APPS,
    )

    assert not is_allowed_cross_app_import(
        source_app="orders",
        target_app="inventory",
        target_module="selectors",
        domain_apps={"orders", "inventory"},
    )
    assert not is_allowed_cross_app_import(
        source_app="orders",
        target_app="inventory",
        target_module="services",
        domain_apps={"orders", "inventory"},
    )
