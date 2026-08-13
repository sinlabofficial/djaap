"""Tests for API permissions module."""

from unittest.mock import MagicMock, patch

from apps.api.permissions import (
    CanAssignRoles,
    CanManageRoles,
    CanManageUsers,
    CanViewUsers,
    HasResourcePermission,
    IsAdminUser,
    IsOwnerOrAdmin,
)


class TestHasResourcePermission:
    """Tests for HasResourcePermission."""

    def test_no_user_returns_false(self):
        """Test that unauthenticated users are denied."""
        permission = HasResourcePermission()
        request = MagicMock()
        request.user = None
        view = MagicMock()

        result = permission.has_permission(request, view)
        assert result is False

    def test_unauthenticated_user_returns_false(self):
        """Test that unauthenticated users are denied."""
        permission = HasResourcePermission()
        request = MagicMock()
        request.user.is_authenticated = False
        view = MagicMock()

        result = permission.has_permission(request, view)
        assert result is False

    def test_no_resource_or_action_returns_true(self):
        """Test that missing resource/action defaults to allowed."""
        permission = HasResourcePermission()
        request = MagicMock()
        request.user.is_authenticated = True
        view = MagicMock()
        view.resource = None
        view.action_permission = None

        result = permission.has_permission(request, view)
        assert result is True

    @patch("apps.api.permissions.check_user_permission")
    def test_checks_permission_when_resource_and_action_set(self, mock_check):
        """Test permission check with resource and action."""
        mock_check.return_value = True
        permission = HasResourcePermission()
        permission.resource = "users"
        permission.action_permission = "view"

        request = MagicMock()
        request.user.is_authenticated = True
        view = MagicMock()

        result = permission.has_permission(request, view)
        assert result is True
        mock_check.assert_called_once()


class TestIsAdminUser:
    """Tests for IsAdminUser permission."""

    def test_superuser_allowed(self):
        """Test superuser is allowed."""
        permission = IsAdminUser()
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_staff = False
        request.user.is_superuser = True
        view = MagicMock()

        result = permission.has_permission(request, view)
        assert result is True

    def test_staff_allowed(self):
        """Test staff user is allowed."""
        permission = IsAdminUser()
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_staff = True
        request.user.is_superuser = False
        view = MagicMock()

        result = permission.has_permission(request, view)
        assert result is True

    def test_regular_user_denied(self):
        """Test regular user is denied."""
        permission = IsAdminUser()
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_staff = False
        request.user.is_superuser = False
        view = MagicMock()

        result = permission.has_permission(request, view)
        assert result is False


class TestIsOwnerOrAdmin:
    """Tests for IsOwnerOrAdmin permission."""

    def test_owner_allowed(self):
        """Test object owner is allowed."""
        permission = IsOwnerOrAdmin()
        user = MagicMock()
        user.is_authenticated = True
        user.is_staff = False
        user.is_superuser = False

        request = MagicMock()
        request.user = user
        view = MagicMock()
        obj = MagicMock()
        obj.user = user

        result = permission.has_object_permission(request, view, obj)
        assert result is True

    def test_admin_allowed(self):
        """Test admin is allowed for any object."""
        permission = IsOwnerOrAdmin()
        admin_user = MagicMock()
        admin_user.is_authenticated = True
        admin_user.is_staff = True

        request = MagicMock()
        request.user = admin_user
        view = MagicMock()
        obj = MagicMock()
        obj.user = MagicMock()  # Different user

        result = permission.has_object_permission(request, view, obj)
        assert result is True

    def test_non_owner_denied(self):
        """Test non-owner is denied."""
        permission = IsOwnerOrAdmin()
        user = MagicMock()
        user.is_authenticated = True
        user.is_staff = False
        user.is_superuser = False

        request = MagicMock()
        request.user = user
        view = MagicMock()
        obj = MagicMock()
        obj.user = MagicMock()  # Different user
        obj.owner = MagicMock()  # Different owner

        result = permission.has_object_permission(request, view, obj)
        assert result is False


class TestPermissionClasses:
    """Tests for concrete permission classes."""

    def test_can_manage_users_attributes(self):
        """Test CanManageUsers has correct attributes."""
        perm = CanManageUsers()
        assert perm.resource == "users"
        assert perm.action_permission == "manage"

    def test_can_view_users_attributes(self):
        """Test CanViewUsers has correct attributes."""
        perm = CanViewUsers()
        assert perm.resource == "users"
        assert perm.action_permission == "view"

    def test_can_manage_roles_attributes(self):
        """Test CanManageRoles has correct attributes."""
        perm = CanManageRoles()
        assert perm.resource == "roles"
        assert perm.action_permission == "manage"

    def test_can_assign_roles_attributes(self):
        """Test CanAssignRoles has correct attributes."""
        perm = CanAssignRoles()
        assert perm.resource == "roles"
        assert perm.action_permission == "assign"
