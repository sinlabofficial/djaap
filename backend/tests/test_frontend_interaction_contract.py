from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from apps.core.models import User


@pytest.fixture
def dashboard_admin():
    return User.objects.create_user(
        email="frontend-contract-admin@example.com",
        password="testpass123",
        is_staff=True,
    )


@pytest.mark.django_db
def test_dashboard_is_server_rendered_with_the_declared_frontend_stack(
    client, dashboard_admin
):
    client.force_login(dashboard_admin)

    response = client.get(reverse("dashboard:home"))
    content = response.content.decode()

    assert response.status_code == 200
    assert '<link rel="stylesheet" href="/static/bundles/main.css">' in content
    assert "alpinejs@3.x.x" in content
    assert "htmx.org@2.0.10" in content
    assert "[x-cloak] { display: none !important; }" in content
    assert "react" not in content.lower()
    assert "vue" not in content.lower()
    assert "svelte" not in content.lower()


@pytest.mark.django_db
def test_public_login_uses_djaapp_branding(client):
    content = client.get(reverse("dashboard:login")).content.decode()

    assert "djaapp" in content
    assert "Djantra" not in content


@pytest.mark.django_db
def test_users_page_uses_htmx_for_server_interactions_and_alpine_for_local_state(
    client, dashboard_admin
):
    client.force_login(dashboard_admin)

    response = client.get(reverse("dashboard:user_list"))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'hx-get="/dashboard/users/table/"' in content
    assert 'hx-target="#users-table-region"' in content
    assert 'hx-trigger="input changed delay:400ms, change"' in content
    assert 'hx-trigger="usersChanged from:body"' in content
    assert 'x-data="{' in content
    assert "fetch(" not in content


@pytest.mark.django_db
def test_htmx_table_request_returns_a_partial_not_a_second_application_shell(
    client, dashboard_admin
):
    client.force_login(dashboard_admin)

    response = client.get(
        reverse("dashboard:users_table"),
        HTTP_HX_REQUEST="true",
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert "<!DOCTYPE html>" not in content
    assert 'id="users-table-region"' not in content
    assert "<table" in content


def test_tailwind_build_produces_a_deployable_dashboard_asset():
    asset = Path(settings.BASE_DIR).parent / "dist" / "bundles" / "main.css"

    assert asset.is_file()
    assert asset.stat().st_size > 0
    assert ".bg-surface" in asset.read_text()
