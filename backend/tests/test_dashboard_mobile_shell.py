import pytest
from django.urls import reverse

from apps.core.models import OrganizationSettings, User


@pytest.mark.django_db
def test_mobile_mode_renders_a_distinct_shell_without_desktop_sidebar(client):
    user = User.objects.create_user(
        email="mobile-shell@example.com",
        password="testpass123",
        presentation_mode="mobile",
    )
    OrganizationSettings.objects.create(mobile_presentation_enabled=True)
    client.force_login(user)

    response = client.get(reverse("dashboard:home"))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'data-testid="mobile-shell"' in content
    assert 'data-testid="mobile-bottom-navigation"' in content
    assert 'data-testid="sidebar-brand-logo"' not in content


@pytest.mark.django_db
def test_mobile_navigation_is_permission_filtered(client):
    user = User.objects.create_user(
        email="mobile-member@example.com",
        password="testpass123",
        presentation_mode="mobile",
    )
    OrganizationSettings.objects.create(mobile_presentation_enabled=True)
    client.force_login(user)

    content = client.get(reverse("dashboard:home")).content.decode()

    assert 'href="/dashboard/"' in content
    assert 'href="/dashboard/profile/"' in content
    assert 'href="/dashboard/settings/"' not in content
