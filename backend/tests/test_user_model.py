"""
Tests for User model - TDD RED phase.

These tests should FAIL initially because UserManager
create_user and create_superuser are not yet implemented.
"""

import pytest
from django.db import IntegrityError

from apps.core.models import User


@pytest.mark.django_db
class TestUserModel:
    """Test User model behavior."""

    def test_user_creation_with_email(self):
        """Test creating user with email only."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")

    def test_user_creation_with_phone(self):
        """Test creating user with phone number."""
        user = User.objects.create_user(
            email="phone@example.com", password="testpass123", phone="+1234567890"
        )
        assert user.phone == "+1234567890"

    def test_user_creation_with_employee_id(self):
        """Test creating user with employee ID."""
        user = User.objects.create_user(
            email="employee@example.com", password="testpass123", employee_id="EMP001"
        )
        assert user.employee_id == "EMP001"

    def test_user_email_unique(self):
        """Test that email must be unique."""
        User.objects.create_user(email="unique@example.com", password="pass123")
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="unique@example.com", password="pass456")

    def test_user_phone_unique_if_provided(self):
        """Test that phone must be unique when provided."""
        User.objects.create_user(
            email="phone1@example.com", password="pass123", phone="+1111111111"
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="phone2@example.com", password="pass456", phone="+1111111111"
            )

    def test_user_employee_id_unique_if_provided(self):
        """Test that employee_id must be unique when provided."""
        User.objects.create_user(
            email="emp1@example.com", password="pass123", employee_id="EMP001"
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="emp2@example.com", password="pass456", employee_id="EMP001"
            )

    def test_user_str_representation(self):
        """Test User string representation."""
        user = User.objects.create_user(email="str@example.com", password="pass123")
        assert str(user) == "str@example.com"

    def test_user_is_active_default(self):
        """Test that user is active by default."""
        user = User.objects.create_user(email="active@example.com", password="pass123")
        assert user.is_active is True

    def test_user_has_uuid_primary_key(self):
        """Test that user has UUID primary key."""
        import uuid

        user = User.objects.create_user(email="uuid@example.com", password="pass123")
        assert isinstance(user.id, uuid.UUID)  # UUID type
        assert len(str(user.id)) == 36  # UUID has 36 characters
