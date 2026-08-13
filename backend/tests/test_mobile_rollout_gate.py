import pytest
from django.urls import reverse

from apps.core.models import OrganizationSettings, User


@pytest.mark.django_db
def test_feature_flag_disabled_keeps_mobile_preference_on_dashboard_shell(client):
    user = User.objects.create_user(
        email="rollout-disabled@example.com",
        password="testpass123",
        presentation_mode="mobile",
    )
    OrganizationSettings.objects.create(mobile_presentation_enabled=False)
    client.force_login(user)

    content = client.get(reverse("dashboard:home")).content.decode()

    assert 'data-testid="mobile-shell"' not in content
    assert 'data-testid="sidebar-brand-logo"' in content


@pytest.mark.django_db
def test_mobile_htmx_partial_never_renders_a_second_shell(client):
    user = User.objects.create_user(
        email="rollout-htmx@example.com",
        password="testpass123",
        presentation_mode="mobile",
        is_staff=True,
    )
    OrganizationSettings.objects.create(mobile_presentation_enabled=True)
    client.force_login(user)

    response = client.get(
        reverse("dashboard:users_table"),
        HTTP_HX_REQUEST="true",
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert "<!DOCTYPE html>" not in content
    assert 'data-testid="mobile-shell"' not in content
    assert "<table" in content
