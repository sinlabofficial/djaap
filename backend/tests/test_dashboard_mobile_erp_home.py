import pytest
from django.urls import reverse

from apps.core.models import OrganizationSettings, User


@pytest.mark.django_db
def test_mobile_presentation_mode_renders_erp_hero_and_app_launcher(client):
    user = User.objects.create_user(
        email="mobile-erp-user@example.com",
        password="testpass123",
        presentation_mode="mobile",
        is_staff=True,
    )
    OrganizationSettings.objects.create(mobile_presentation_enabled=True)
    client.force_login(user)

    response = client.get(reverse("dashboard:home"))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'data-testid="mobile-erp-hero"' in content
    assert 'data-testid="mobile-app-launcher"' in content
    assert 'href="/dashboard/users/"' in content
    assert 'href="/dashboard/roles/"' in content
