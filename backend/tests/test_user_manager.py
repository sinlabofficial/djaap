"""
Tests for UserManager - TDD RED phase.

These tests should FAIL initially because create_user
and create_superuser are not yet implemented (raise NotImplementedError).
"""

import pytest

from apps.core.models import User


@pytest.mark.django_db
class TestUserManager:
    """Test UserManager methods."""

    def test_create_user_with_email(self):
        """Test UserManager.create_user with email."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_normalizes_email(self):
        """Test that create_user normalizes email to lowercase."""
        user = User.objects.create_user(
            email="USER@Example.COM", password="testpass123"
        )
        assert user.email == "user@example.com"

    def test_create_user_with_password(self):
        """Test that create_user properly hashes password."""
        user = User.objects.create_user(
            email="password@example.com", password="testpass123"
        )
        assert user.password != "testpass123"  # Password should be hashed
        assert user.check_password("testpass123")  # Should verify correctly

    def test_create_superuser_is_staff(self):
        """Test that create_superuser sets is_staff=True."""
        user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        assert user.is_staff is True

    def test_create_superuser_is_superuser(self):
        """Test that create_superuser sets is_superuser=True."""
        user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        assert user.is_superuser is True

    def test_create_user_without_email_raises_error(self):
        """Test that create_user raises error without email."""
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="testpass123")

    def test_create_superuser_is_active(self):
        """Test that create_superuser sets is_active=True."""
        user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        assert user.is_active is True
