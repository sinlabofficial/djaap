"""
Integration tests for role assignment and permission resolution.

Tests the complete flow of:
1. Creating roles and permissions
2. Assigning permissions to roles
3. Assigning roles to users
4. Checking permissions
"""

import pytest

from apps.core.models import Permission, Role, User, UserRole
from apps.core.services import (
    assign_role_to_user,
    check_user_permission,
    remove_role_from_user,
)


@pytest.mark.django_db
class TestRolePermissionIntegration:
    """Integration tests for role and permission system."""

    def setup_method(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="roleuser@example.com", password="testpass123"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )

        # Create roles
        self.staff_role = Role.objects.create(name="Staff", level=20)
        self.manager_role = Role.objects.create(name="Manager", level=60)

        # Create permissions
        self.view_perm = Permission.objects.create(
            resource="items", action="view", description="Can view items"
        )
        self.create_perm = Permission.objects.create(
            resource="items", action="create", description="Can create items"
        )
        self.delete_perm = Permission.objects.create(
            resource="items", action="delete", description="Can delete items"
        )

    def test_superuser_has_all_permissions(self):
        """Test that superuser has all permissions automatically."""
        has_view = check_user_permission(self.admin_user, "items", "view")
        has_create = check_user_permission(self.admin_user, "items", "create")
        has_delete = check_user_permission(self.admin_user, "items", "delete")

        assert has_view is True
        assert has_create is True
        assert has_delete is True

    def test_regular_user_has_no_permissions_by_default(self):
        """Test that regular user has no permissions without roles."""
        has_perm = check_user_permission(self.user, "items", "view")
        assert has_perm is False

    def test_assign_role_with_permission(self):
        """Test assigning a role with permission to user."""
        # Assign view permission to staff role
        self.staff_role.permissions.add(self.view_perm)

        # Assign staff role to user
        assign_role_to_user(
            user=self.user, role=self.staff_role, assigned_by=self.admin_user
        )

        # User should now have view permission
        has_view = check_user_permission(self.user, "items", "view")
        assert has_view is True

        # But not create permission
        has_create = check_user_permission(self.user, "items", "create")
        assert has_create is False

    def test_user_with_multiple_roles_union_permissions(self):
        """Test that user with multiple roles gets union of permissions."""
        # Staff role has view permission
        self.staff_role.permissions.add(self.view_perm)
        # Manager role has create permission
        self.manager_role.permissions.add(self.create_perm)

        # Assign both roles to user
        assign_role_to_user(
            user=self.user, role=self.staff_role, assigned_by=self.admin_user
        )
        assign_role_to_user(
            user=self.user, role=self.manager_role, assigned_by=self.admin_user
        )

        # User should have both permissions (union)
        has_view = check_user_permission(self.user, "items", "view")
        has_create = check_user_permission(self.user, "items", "create")

        assert has_view is True
        assert has_create is True

    def test_remove_role_revokes_permissions(self):
        """Test that removing a role revokes its permissions."""
        # Assign view permission to staff role
        self.staff_role.permissions.add(self.view_perm)

        # Assign staff role to user
        assign_role_to_user(
            user=self.user, role=self.staff_role, assigned_by=self.admin_user
        )

        # User should have permission
        assert check_user_permission(self.user, "items", "view") is True

        # Remove the role
        remove_role_from_user(user=self.user, role=self.staff_role)

        # User should no longer have permission
        assert check_user_permission(self.user, "items", "view") is False

    def test_assign_same_role_twice_fails(self):
        """Test that assigning the same role twice returns False."""
        # First assignment
        result1 = assign_role_to_user(
            user=self.user, role=self.staff_role, assigned_by=self.admin_user
        )
        assert result1 is True

        # Second assignment should fail
        result2 = assign_role_to_user(
            user=self.user, role=self.staff_role, assigned_by=self.admin_user
        )
        assert result2 is False

        # Should only have one UserRole record
        assert (
            UserRole.objects.filter(user=self.user, role=self.staff_role).count() == 1
        )

    def test_remove_unassigned_role_returns_false(self):
        """Test that removing a role that wasn't assigned returns False."""
        result = remove_role_from_user(user=self.user, role=self.staff_role)
        assert result is False
