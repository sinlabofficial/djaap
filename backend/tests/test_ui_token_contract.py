from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ui_tokens_match_design_system_contract():
    tokens = (ROOT / "ui" / "tokens.css").read_text()
    main_css = (ROOT / "ui" / "main.css").read_text()
    design = (ROOT / "design.md").read_text()

    assert "--ui-font-sans: Inter" in tokens
    assert "--ui-font-mono: 'JetBrains Mono'" in tokens
    assert "--ui-primary: #0f6b63" in tokens
    assert "--ui-on-primary: #f5fffc" in tokens
    assert "--ui-success:" in tokens
    assert "--ui-warning:" in tokens
    assert "--ui-background:" in tokens
    assert "--ui-on-surface-variant:" in tokens
    assert "--color-on-surface-variant: var(--ui-on-surface-variant)" in main_css
    assert "--color-success: var(--ui-success)" in main_css
    assert "primary: '#0f6b63'" in design


def test_component_contract_exposes_catalog_and_accessibility_baseline():
    catalog = (ROOT / "docs" / "guides" / "frontend-component-catalog.md").read_text()
    components = (ROOT / "frontend" / "layouts" / "_components.html").read_text()

    for component in (
        "button",
        "input",
        "textarea",
        "select",
        "card",
        "badge",
        "modal",
        "toast",
    ):
        assert f"partialdef {component}" in components
    assert "presentation data only" in catalog
    assert "WCAG 2.2 AA" in catalog
    assert "44px touch targets" in catalog


def test_shared_component_inventory_is_complete():
    components = (ROOT / "frontend" / "layouts" / "_components.html").read_text()

    for component in (
        "button",
        "icon_button",
        "input",
        "textarea",
        "select",
        "checkbox",
        "form_field",
        "card",
        "badge",
        "alert",
        "toast",
        "modal",
        "confirm_dialog",
        "drawer",
        "table",
        "data_list",
        "pagination",
        "empty_state",
        "loading_state",
        "skeleton",
    ):
        assert f"partialdef {component}" in components

    assert 'aria-label="{{ label }}"' in components
    assert "aria-describedby" in components
    assert "focus-visible:ring-2 focus-visible:ring-primary" in components


def test_mobile_interaction_patterns_have_responsive_contracts():
    components = (ROOT / "frontend" / "layouts" / "_components.html").read_text()

    for component in (
        "sticky_form_actions",
        "responsive_modal",
        "mobile_sheet",
        "responsive_table",
    ):
        assert f"partialdef {component}" in components
    assert 'data-testid="mobile-form-actions"' in components
    assert "env(safe-area-inset-bottom)" in components
    assert "max-h-[calc(100dvh-2rem)]" in components
    assert "overflow-x-auto" in components
