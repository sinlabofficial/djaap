"""
Integration tests for authentication with all identifiers.

Tests end-to-end login with email, phone, and employee_id.
"""

import pytest
from django.contrib.auth import authenticate

from apps.core.models import User


@pytest.mark.django_db
class TestLoginIntegration:
    """Integration tests for multi-identifier login."""

    def setup_method(self):
        """Set up test user with all identifiers."""
        self.user = User.objects.create_user(
            email="integration@example.com",
            password="testpass123",
            phone="+9876543210",
            employee_id="EMP999",
        )

    def test_login_with_email(self):
        """Test login with email using Django authenticate."""
        user = authenticate(
            None, identifier="integration@example.com", password="testpass123"
        )
        assert user is not None
        assert user.email == "integration@example.com"

    def test_login_with_phone(self):
        """Test login with phone using Django authenticate."""
        user = authenticate(None, identifier="+9876543210", password="testpass123")
        assert user is not None
        assert user.phone == "+9876543210"

    def test_login_with_employee_id(self):
        """Test login with employee_id using Django authenticate."""
        user = authenticate(None, identifier="EMP999", password="testpass123")
        assert user is not None
        assert user.employee_id == "EMP999"

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns None."""
        user = authenticate(
            None, identifier="integration@example.com", password="wrongpassword"
        )
        assert user is None

    def test_login_nonexistent_user(self):
        """Test login with non-existent user returns None."""
        user = authenticate(
            None, identifier="nonexistent@example.com", password="testpass123"
        )
        assert user is None

    def test_login_inactive_user(self):
        """Test login with inactive user returns None."""
        self.user.is_active = False
        self.user.save()

        user = authenticate(
            None, identifier="integration@example.com", password="testpass123"
        )
        assert user is None

    def test_login_email_case_insensitive(self):
        """Test login with email is case-insensitive."""
        user = authenticate(
            None, identifier="INTEGRATION@EXAMPLE.COM", password="testpass123"
        )
        assert user is not None
        assert user.email == "integration@example.com"
