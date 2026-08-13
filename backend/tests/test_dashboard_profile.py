import pytest
from auditlog.models import LogEntry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.core.models import User


def png_file(*, name="avatar.png", size=68):
    content = b"\x89PNG\r\n\x1a\n" + (b"0" * max(0, size - 8))
    return SimpleUploadedFile(name, content, content_type="image/png")


@pytest.mark.django_db
class TestDashboardProfile:
    def setup_method(self):
        self.client = Client()

    def test_authenticated_user_can_render_profile_page(self):
        user = User.objects.create_user(
            email="profile@example.com",
            password="testpass123",
            profile_name="Profile User",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("dashboard:profile"))

        assert response.status_code == 200
        assert b"My Profile" in response.content
        assert b"Profile User" in response.content
        assert b"profile@example.com" in response.content

    def test_unauthenticated_user_is_redirected_from_profile(self):
        response = self.client.get(reverse("dashboard:profile"))

        assert response.status_code == 302
        assert "/dashboard/login/" in response["Location"]

    def test_user_can_update_profile_and_password(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        user = User.objects.create_user(
            email="profile@example.com", password="testpass123"
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("dashboard:profile"),
            {
                "profile_name": "Updated Profile",
                "current_password": "testpass123",
                "new_password": "newpass123",
                "new_password_confirm": "newpass123",
                "profile_photo": png_file(),
            },
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.profile_name == "Updated Profile"
        assert user.check_password("newpass123")
        assert user.profile_photo.name.startswith("profile_photos/")
        assert LogEntry.objects.filter(
            object_pk=str(user.id), action=LogEntry.Action.UPDATE
        ).exists()

        user.profile_photo.delete(save=False)

    def test_user_can_clear_existing_profile_photo(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        user = User.objects.create_user(
            email="clear-photo@example.com",
            password="testpass123",
            profile_name="Photo User",
        )
        user.profile_photo.save("existing.png", png_file(), save=True)
        self.client.force_login(user)

        response = self.client.post(
            reverse("dashboard:profile"),
            {
                "profile_name": "Photo User",
                "profile_photo-clear": "on",
            },
        )

        assert response.status_code == 200
        assert b"Profile updated successfully." in response.content
        user.refresh_from_db()
        assert not user.profile_photo

    def test_wrong_current_password_keeps_profile_unchanged(self):
        user = User.objects.create_user(
            email="profile@example.com",
            password="testpass123",
            profile_name="Original Profile",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("dashboard:profile"),
            {
                "profile_name": "Changed Profile",
                "current_password": "wrong-password",
                "new_password": "newpass123",
                "new_password_confirm": "newpass123",
            },
        )

        assert response.status_code == 200
        assert b"Current password is incorrect." in response.content
        user.refresh_from_db()
        assert user.profile_name == "Original Profile"
        assert user.check_password("testpass123")

    def test_mismatched_new_password_is_rejected(self):
        user = User.objects.create_user(
            email="profile@example.com", password="testpass123"
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("dashboard:profile"),
            {
                "profile_name": "Updated Profile",
                "current_password": "testpass123",
                "new_password": "newpass123",
                "new_password_confirm": "different123",
            },
        )

        assert response.status_code == 200
        assert b"New passwords do not match." in response.content
        user.refresh_from_db()
        assert not user.profile_name
        assert user.check_password("testpass123")

    def test_oversized_profile_photo_is_rejected(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        user = User.objects.create_user(
            email="profile@example.com", password="testpass123"
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("dashboard:profile"),
            {
                "profile_name": "Updated Profile",
                "profile_photo": SimpleUploadedFile(
                    "avatar.png",
                    b"0" * (2 * 1024 * 1024 + 1),
                    content_type="image/png",
                ),
            },
        )

        assert response.status_code == 200
        assert b"Profile photo must be 2 MB or smaller." in response.content
        user.refresh_from_db()
        assert user.profile_name == ""
        assert not user.profile_photo

    def test_password_change_does_not_write_password_value_to_audit_log(self):
        user = User.objects.create_user(
            email="profile@example.com", password="testpass123"
        )
        self.client.force_login(user)

        self.client.post(
            reverse("dashboard:profile"),
            {
                "profile_name": "Password User",
                "current_password": "testpass123",
                "new_password": "newpass123",
                "new_password_confirm": "newpass123",
            },
        )

        logs = LogEntry.objects.filter(
            object_pk=str(user.id), action=LogEntry.Action.UPDATE
        )
        assert logs.exists()
        assert all("newpass123" not in str(log.changes) for log in logs)

    def test_password_change_creates_audit_event_without_password_value(self):
        user = User.objects.create_user(
            email="password-only@example.com",
            password="testpass123",
            profile_name="Existing Profile",
        )
        self.client.force_login(user)

        before = LogEntry.objects.filter(
            object_pk=str(user.id), action=LogEntry.Action.UPDATE
        ).count()
        self.client.post(
            reverse("dashboard:profile"),
            {
                "profile_name": "Existing Profile",
                "current_password": "testpass123",
                "new_password": "newpass123",
                "new_password_confirm": "newpass123",
            },
        )

        logs = LogEntry.objects.filter(
            object_pk=str(user.id), action=LogEntry.Action.UPDATE
        )
        assert logs.count() > before
        assert all("newpass123" not in str(log.changes) for log in logs)
