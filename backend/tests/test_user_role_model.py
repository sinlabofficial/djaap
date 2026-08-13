"""
Tests for UserRole model - TDD RED phase.

UserRole is the many-to-many relationship between User and Role.
"""

import pytest
from django.db import IntegrityError

from apps.core.models import Role, User, UserRole


@pytest.mark.django_db
class TestUserRoleModel:
    """Test UserRole model behavior."""

    def setup_method(self):
        """Set up test user and role."""
        self.user = User.objects.create_user(
            email="userrole@example.com", password="testpass123"
        )
        self.role = Role.objects.create(name="Manager", level=60)

    def test_assign_role_to_user(self):
        """Test assigning a role to a user."""
        user_role = UserRole.objects.create(
            user=self.user, role=self.role, assigned_by=self.user
        )
        assert user_role.user == self.user
        assert user_role.role == self.role

    def test_user_can_have_multiple_roles(self):
        """Test that a user can have multiple roles."""
        role2 = Role.objects.create(name="Admin", level=80)

        UserRole.objects.create(user=self.user, role=self.role)
        UserRole.objects.create(user=self.user, role=role2)

        assert UserRole.objects.filter(user=self.user).count() == 2

    def test_role_can_have_multiple_users(self):
        """Test that a role can be assigned to multiple users."""
        user2 = User.objects.create_user(
            email="user2@example.com", password="testpass123"
        )

        UserRole.objects.create(user=self.user, role=self.role)
        UserRole.objects.create(user=user2, role=self.role)

        assert UserRole.objects.filter(role=self.role).count() == 2

    def test_user_role_unique_together(self):
        """Test that user+role combination must be unique."""
        UserRole.objects.create(user=self.user, role=self.role)
        with pytest.raises(IntegrityError):
            UserRole.objects.create(user=self.user, role=self.role)

    def test_user_role_has_assigned_at_timestamp(self):
        """Test that user_role has assigned_at timestamp."""
        user_role = UserRole.objects.create(
            user=self.user, role=self.role, assigned_by=self.user
        )
        assert user_role.assigned_at is not None
