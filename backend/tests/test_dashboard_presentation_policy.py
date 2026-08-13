import pytest
from django.urls import reverse

from apps.core.models import OrganizationSettings, Role, User


@pytest.mark.django_db
def test_user_can_update_own_presentation_preference_from_profile(client):
    user = User.objects.create_user(
        email="policy-profile@example.com",
        password="testpass123",
    )
    OrganizationSettings.objects.create(mobile_presentation_enabled=True)
    client.force_login(user)

    response = client.post(
        reverse("dashboard:profile"),
        {
            "profile_name": "Mobile Operator",
            "presentation_mode": "mobile",
            "current_password": "",
            "new_password": "",
            "new_password_confirm": "",
        },
    )

    assert response.status_code == 200
    assert User.objects.get(pk=user.pk).presentation_mode == "mobile"


@pytest.mark.django_db
def test_staff_can_update_organization_presentation_policy(client):
    staff = User.objects.create_user(
        email="policy-organization@example.com",
        password="testpass123",
        is_staff=True,
    )
    client.force_login(staff)

    response = client.post(
        reverse("dashboard:settings"),
        {
            "tab": "basic",
            "organization_name": "Acme",
            "description": "",
            "address": "",
            "phone": "",
            "email": "",
            "presentation_mode": "mobile",
            "mobile_presentation_enabled": "on",
        },
    )

    assert response.status_code == 200
    organization = OrganizationSettings.objects.get()
    assert organization.presentation_mode == "mobile"
    assert organization.mobile_presentation_enabled is True


@pytest.mark.django_db
def test_staff_can_update_role_presentation_policy(client):
    staff = User.objects.create_user(
        email="policy-role@example.com",
        password="testpass123",
        is_staff=True,
    )
    role = Role.objects.create(name="Operator", level=10)
    client.force_login(staff)

    response = client.post(
        reverse("dashboard:role_edit", args=[role.pk]),
        {
            "name": "Operator",
            "level": "10",
            "description": "",
            "presentation_mode_policy": "mobile",
        },
    )

    assert response.status_code in {200, 302}
    assert Role.objects.get(pk=role.pk).presentation_mode_policy == "mobile"
