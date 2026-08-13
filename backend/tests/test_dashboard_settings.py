"""Behavior tests for the administrator settings page."""

import pytest
from auditlog.models import LogEntry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.core.models import OrganizationSettings, User


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        email="settings-admin@example.com",
        password="testpass123",
        is_staff=True,
    )


@pytest.fixture
def regular_user():
    return User.objects.create_user(
        email="settings-member@example.com",
        password="testpass123",
    )


@pytest.mark.django_db
class TestDashboardSettings:
    def setup_method(self):
        self.client = Client()

    def test_settings_requires_admin_or_superuser(self, regular_user):
        self.client.force_login(regular_user)

        response = self.client.get(reverse("dashboard:settings"))

        assert response.status_code == 302
        assert "/dashboard/login/" in response["Location"]

    def test_staff_can_render_settings_tabs_and_menu(self, staff_user):
        self.client.force_login(staff_user)

        response = self.client.get(reverse("dashboard:settings"))

        assert response.status_code == 200
        assert b'<div class="space-y-6 pb-24' not in response.content
        assert b'<div class="space-y-6">' in response.content
        assert b'mx-auto max-w-6xl' not in response.content
        assert b"Basic information" in response.content
        assert b"User" in response.content
        assert b"Roles" in response.content
        assert b"Authentication" in response.content
        assert b"/dashboard/settings/" in response.content

    def test_users_tab_contains_user_management(self, staff_user):
        self.client.force_login(staff_user)

        response = self.client.get(reverse("dashboard:settings") + "?tab=users")

        assert response.status_code == 200
        assert b"users-table-region" in response.content
        assert b"user-search" in response.content
        assert b"Create User" in response.content

    def test_roles_tab_contains_roles_and_permissions(self, staff_user):
        self.client.force_login(staff_user)

        response = self.client.get(reverse("dashboard:settings") + "?tab=roles")

        assert response.status_code == 200
        assert b"roles-table-region" in response.content
        assert b"role-detail-panel" in response.content

    def test_staff_sidebar_no_longer_has_users_or_roles_entries(self, staff_user):
        self.client.force_login(staff_user)

        response = self.client.get(reverse("dashboard:home"))

        assert response.status_code == 200
        assert b">Users</span>" not in response.content
        assert b">Roles</span>" not in response.content
        assert b'href="/dashboard/settings/"' in response.content

    def test_sidebar_brand_logo_remains_rendered_when_collapsed(self, staff_user, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        OrganizationSettings.objects.create(
            organization_name="Acme Operations",
            logo=SimpleUploadedFile("brand.png", b"fake-image", content_type="image/png"),
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse("dashboard:home"))

        assert response.status_code == 200
        assert b'data-testid="sidebar-brand-logo"' in response.content
        assert b'<a id="sidebar-brand" x-show="!sidebarCollapsed"' not in response.content

    def test_topbar_replaces_search_with_sidebar_toggle(self, staff_user):
        self.client.force_login(staff_user)

        response = self.client.get(reverse("dashboard:home"))

        assert response.status_code == 200
        assert b'data-testid="topbar-sidebar-toggle"' in response.content
        assert b'data-testid="sidebar-toggle"' not in response.content
        assert b'id="topbar-search"' not in response.content
        assert b'data-testid="topbar-left-controls"' in response.content
        assert b'class="relative flex h-16 items-center gap-1 border-b border-outline-variant p-2' in response.content
        assert b'class="h-7 w-7 overflow-hidden rounded-lg' in response.content
        assert b'class="hidden h-8 w-8 items-center justify-center rounded-lg' in response.content
        assert b"bg-transparent" in response.content
        assert b"shadow-none" in response.content
        assert b"hover:bg-transparent" in response.content
        assert b"hover:shadow-none" in response.content

    def test_settings_menu_is_hidden_for_regular_user(self, regular_user):
        self.client.force_login(regular_user)

        response = self.client.get(reverse("dashboard:home"))

        assert response.status_code == 200
        assert b'href="/dashboard/settings/"' not in response.content

    def test_staff_can_update_organization_information_and_audit_it(self, staff_user):
        self.client.force_login(staff_user)
        logo = SimpleUploadedFile("logo.png", b"fake-image", content_type="image/png")

        response = self.client.post(
            reverse("dashboard:settings"),
            {
                "organization_name": "Acme Operations",
                "description": "Internal operations platform",
                "address": "Jl. Merdeka 1",
                "phone": "+6221000000",
                "email": "hello@acme.example",
                "logo": logo,
                "tab": "basic",
            },
        )

        assert response.status_code == 200
        organization = OrganizationSettings.objects.get()
        assert organization.organization_name == "Acme Operations"
        assert organization.description == "Internal operations platform"
        assert organization.logo.name.endswith(".png")
        assert LogEntry.objects.filter(
            object_pk=str(organization.id), action=LogEntry.Action.UPDATE
        ).exists()

    def test_invalid_organization_information_is_rejected(self, staff_user):
        self.client.force_login(staff_user)

        response = self.client.post(
            reverse("dashboard:settings"),
            {
                "organization_name": "",
                "description": "Invalid organization",
                "email": "not-an-email",
                "tab": "basic",
            },
        )

        assert response.status_code == 200
        assert b"This field is required" in response.content
        assert b"Enter a valid email address" in response.content
        assert not OrganizationSettings.objects.exists()

    def test_staff_can_clear_existing_organization_logo(self, staff_user, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        organization = OrganizationSettings.objects.create(
            organization_name="Acme Operations",
            logo=SimpleUploadedFile("existing.png", b"fake-image", content_type="image/png"),
        )
        self.client.force_login(staff_user)

        response = self.client.post(
            reverse("dashboard:settings"),
            {
                "organization_name": "Acme Operations",
                "tab": "basic",
                "logo-clear": "on",
            },
        )

        assert response.status_code == 200
        organization.refresh_from_db()
        assert not organization.logo
