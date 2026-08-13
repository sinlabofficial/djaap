import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.core.models import Permission, Role, User, UserRole


@pytest.fixture
def staff_user():
    user = User.objects.create_user(
        email="transfer-admin@example.com",
        password="testpass123",
        is_staff=True,
    )
    permission = Permission.objects.create(resource="users", action="manage")
    role = Role.objects.create(name="Transfer Manager", level=20)
    role.permissions.add(permission)
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.mark.django_db
class TestDashboardUserImportExport:
    def setup_method(self):
        self.client = Client()

    def test_export_csv_excludes_passwords(self, staff_user):
        User.objects.create_user(email="export@example.com", password="secret123")
        self.client.force_login(staff_user)

        response = self.client.get(reverse("dashboard:user_export") + "?format=csv")

        assert response.status_code == 200
        assert response["Content-Disposition"] == 'attachment; filename="users.csv"'
        assert b"email,phone,employee_id,profile_name,is_staff,is_active" in response.content
        assert b"password" in response.content
        assert b",password\r\n" in response.content
        assert b"export@example.com" in response.content

    def test_xls_template_has_import_headers(self, staff_user):
        self.client.force_login(staff_user)

        response = self.client.get(
            reverse("dashboard:user_import_template") + "?format=xls"
        )

        assert response.status_code == 200
        assert response["Content-Disposition"] == (
            'attachment; filename="user-import-template.xls"'
        )
        assert b"email" in response.content
        assert b"password" in response.content

    def test_import_csv_creates_and_updates_users(self, staff_user):
        existing = User.objects.create_user(
            email="existing@example.com", password="oldpass123"
        )
        content = (
            b"email,phone,employee_id,profile_name,is_staff,is_active,password\n"
            b"existing@example.com,0812,E-1,Updated Name,true,false,newpass123\n"
            b"new@example.com,0813,E-2,New User,false,true,newpass456\n"
        )
        self.client.force_login(staff_user)

        response = self.client.post(
            reverse("dashboard:user_import"),
            {"file": SimpleUploadedFile("users.csv", content, content_type="text/csv")},
        )

        assert response.status_code == 302
        existing.refresh_from_db()
        assert existing.phone == "0812"
        assert existing.is_staff is True
        assert existing.is_active is False
        assert existing.profile_name == "Updated Name"
        assert existing.check_password("newpass123")
        assert User.objects.filter(email="new@example.com").exists()

    def test_import_is_atomic_when_a_row_is_invalid(self, staff_user):
        content = (
            b"email,phone,employee_id,profile_name,is_staff,is_active,password\n"
            b"valid@example.com,,,,false,true,validpass123\n"
            b"invalid-email,,,,false,true,validpass123\n"
        )
        self.client.force_login(staff_user)

        response = self.client.post(
            reverse("dashboard:user_import"),
            {"file": SimpleUploadedFile("users.csv", content, content_type="text/csv")},
        )

        assert response.status_code == 200
        assert b"email is invalid" in response.content
        assert not User.objects.filter(email="valid@example.com").exists()

    def test_malformed_csv_is_a_validation_error(self, staff_user):
        self.client.force_login(staff_user)

        response = self.client.post(
            reverse("dashboard:user_import"),
            {
                "file": SimpleUploadedFile(
                    "users.csv", b"\xff\xfe\xfa", content_type="text/csv"
                )
            },
        )

        assert response.status_code == 200
        assert b"CSV file is malformed" in response.content

    def test_import_rejects_duplicate_phone_without_writing(self, staff_user):
        User.objects.create_user(email="existing@example.com", phone="0812000")
        content = (
            b"email,phone,employee_id,profile_name,is_staff,is_active,password\n"
            b"new@example.com,0812000,,,false,true,newpass123\n"
        )
        self.client.force_login(staff_user)

        response = self.client.post(
            reverse("dashboard:user_import"),
            {"file": SimpleUploadedFile("users.csv", content, content_type="text/csv")},
        )

        assert response.status_code == 200
        assert b"phone already belongs" in response.content
        assert not User.objects.filter(email="new@example.com").exists()

    def test_regular_user_cannot_import_or_export(self):
        user = User.objects.create_user(
            email="regular@example.com", password="testpass123"
        )
        self.client.force_login(user)

        assert self.client.get(reverse("dashboard:user_export")).status_code == 302
        assert self.client.post(reverse("dashboard:user_import")).status_code == 302

    def test_non_staff_permission_holder_cannot_bulk_transfer_users(self):
        user = User.objects.create_user(
            email="permission-holder@example.com", password="testpass123"
        )
        permission = Permission.objects.create(resource="users", action="manage")
        role = Role.objects.create(name="User Manager", level=10)
        role.permissions.add(permission)
        UserRole.objects.create(user=user, role=role)
        self.client.force_login(user)

        assert self.client.get(reverse("dashboard:user_export")).status_code == 302

    def test_staff_without_manage_permission_cannot_bulk_transfer_users(self):
        user = User.objects.create_user(
            email="staff-without-permission@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(user)

        assert self.client.get(reverse("dashboard:user_export")).status_code == 302
