"""Regression tests for session-authenticated dashboard API access."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.core.models import Role, User


@pytest.mark.django_db
class TestDashboardSessionAuth:
    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            email="dashboard-admin@example.com",
            password="testpass123",
        )
        Role.objects.create(name="Admin", level=100)

    def test_session_user_can_read_current_user_api(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("api:me"))

        assert response.status_code == 200
        assert response.json()["email"] == self.user.email

    def test_session_user_can_read_roles_api(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("api:role-list"))

        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_session_superuser_can_read_users_api(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("api:user-list"))

        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_dashboard_session_check_returns_bootstrap_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:check_session"))

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user"]["email"] == self.user.email
        assert data["user"]["is_staff"] is True

    def test_anonymous_session_check_is_unauthorized(self):
        response = self.client.get(reverse("dashboard:check_session"))

        assert response.status_code == 401
        assert response.json() == {"authenticated": False}

    def test_login_page_renders_for_anonymous_user(self):
        response = self.client.get(reverse("dashboard:login"))

        assert response.status_code == 200

    def test_login_rejects_missing_credentials(self):
        response = self.client.post(reverse("dashboard:login"), {})

        assert response.status_code == 200
        assert b"Please provide both identifier and password." in response.content

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            reverse("dashboard:login"),
            {"identifier": self.user.email, "password": "wrong-password"},
        )

        assert response.status_code == 200
        assert b"Invalid credentials." in response.content

    def test_login_creates_session_and_honors_safe_next_url(self):
        response = self.client.post(
            reverse("dashboard:login") + "?next=/dashboard/profile/",
            {
                "identifier": self.user.email,
                "password": "testpass123",
                "remember_me": "on",
            },
        )

        assert response.status_code == 302
        assert response["Location"] == "/dashboard/profile/"
        assert self.client.session.get_expiry_age() > 0

    def test_authenticated_user_is_redirected_from_login(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:login"))

        assert response.status_code == 302
        assert response["Location"].endswith("/dashboard/")

    def test_logout_requires_post_and_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("dashboard:logout"))

        assert response.status_code == 302
        assert response["Location"].endswith("/dashboard/login/")
