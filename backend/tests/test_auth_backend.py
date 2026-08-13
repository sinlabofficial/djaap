"""
Tests for MultiIdentifierAuthBackend - TDD RED phase.

These tests should FAIL initially because the backend
authenticate and get_user methods are not yet implemented.
"""

import pytest

from apps.core.backends import MultiIdentifierAuthBackend
from apps.core.models import User


@pytest.mark.django_db
class TestAuthBackend:
    """Test MultiIdentifierAuthBackend."""

    def setup_method(self):
        """Set up test user and backend."""
        self.backend = MultiIdentifierAuthBackend()
        self.user = User.objects.create_user(
            email="auth@example.com",
            password="testpass123",
            phone="+1234567890",
            employee_id="EMP001",
        )

    def test_authenticate_with_email(self):
        """Test authentication with email."""
        user = self.backend.authenticate(
            None, identifier="auth@example.com", password="testpass123"
        )
        assert user is not None
        assert user.email == "auth@example.com"

    def test_authenticate_with_username_kwarg(self):
        """Test Django-compatible username kwarg maps to identifier."""
        user = self.backend.authenticate(
            None, username="auth@example.com", password="testpass123"
        )
        assert user is not None
        assert user.email == "auth@example.com"

    def test_authenticate_with_phone(self):
        """Test authentication with phone number."""
        user = self.backend.authenticate(
            None, identifier="+1234567890", password="testpass123"
        )
        assert user is not None
        assert user.email == "auth@example.com"

    def test_authenticate_with_employee_id(self):
        """Test authentication with employee ID."""
        user = self.backend.authenticate(
            None, identifier="EMP001", password="testpass123"
        )
        assert user is not None
        assert user.email == "auth@example.com"

    def test_authenticate_invalid_identifier(self):
        """Test authentication with non-existent identifier."""
        user = self.backend.authenticate(
            None, identifier="nonexistent@example.com", password="testpass123"
        )
        assert user is None

    def test_authenticate_wrong_password(self):
        """Test authentication with wrong password."""
        user = self.backend.authenticate(
            None, identifier="auth@example.com", password="wrongpassword"
        )
        assert user is None

    def test_authenticate_inactive_user(self):
        """Test authentication with inactive user."""
        self.user.is_active = False
        self.user.save()

        user = self.backend.authenticate(
            None, identifier="auth@example.com", password="testpass123"
        )
        assert user is None

    def test_authenticate_soft_deleted_user(self):
        """Test authentication rejects soft-deleted users."""
        self.user.delete()

        user = self.backend.authenticate(
            None, identifier="auth@example.com", password="testpass123"
        )
        assert user is None

    def test_authenticate_does_not_write_stdout(self, capsys):
        """Authentication should not print credentials or status to stdout."""
        self.backend.authenticate(
            None, identifier="auth@example.com", password="testpass123"
        )

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_get_user_active(self):
        """Test get_user returns active user."""
        user = self.backend.get_user(self.user.id)
        assert user is not None
        assert user.email == "auth@example.com"

    def test_get_user_inactive(self):
        """Test get_user returns None for inactive user."""
        self.user.is_active = False
        self.user.save()

        user = self.backend.get_user(self.user.id)
        assert user is None
