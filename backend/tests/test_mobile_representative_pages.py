import pytest
from django.urls import reverse

from apps.core.models import OrganizationSettings, Permission, Role, User, UserRole


@pytest.mark.django_db
def test_representative_dashboard_pages_use_the_same_routes_in_mobile_mode(client):
    user = User.objects.create_user(
        email="mobile-pages-admin@example.com",
        password="testpass123",
        is_staff=True,
        presentation_mode="mobile",
    )
    role = Role.objects.create(name="Mobile Runtime Viewer", level=10)
    permission = Permission.objects.create(resource="runtime_logs", action="view")
    role.permissions.add(permission)
    UserRole.objects.create(user=user, role=role)
    OrganizationSettings.objects.create(mobile_presentation_enabled=True)
    client.force_login(user)

    for route_name in (
        "dashboard:home",
        "dashboard:profile",
        "dashboard:user_list",
        "dashboard:role_list",
        "dashboard:settings",
        "dashboard:logs",
    ):
        response = client.get(reverse(route_name))
        content = response.content.decode()
        assert response.status_code == 200, route_name
        assert 'data-testid="mobile-shell"' in content, route_name
        assert '/mobile/' not in content, route_name


@pytest.mark.django_db
def test_login_remains_a_responsive_auth_shell_with_starterkit_primary(client):
    content = client.get(reverse("dashboard:login")).content.decode()

    assert 'data-testid="auth-shell"' in content
    assert "bg-primary" in content
    assert "#004ac6" not in content
