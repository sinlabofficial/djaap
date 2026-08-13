"""Custom permission classes for API endpoints."""

from rest_framework import permissions

from apps.core.services import check_user_permission


class HasResourcePermission(permissions.BasePermission):
    """
    Permission class that checks if user has permission for a specific resource and action.

    Usage:
        permission_classes = [IsAuthenticated, HasResourcePermission]
        resource = 'users'
        action = 'view'
    """

    resource = None
    action_permission = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        resource = getattr(view, "resource", self.resource)
        action = getattr(view, "action_permission", self.action_permission)

        if not resource or not action:
            return True

        return check_user_permission(request.user, resource, action)


class IsAdminUser(permissions.BasePermission):
    """
    Permission class that allows access only to admin users.

    Admin users are either:
    - Superusers
    - Users with is_staff=True
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class that allows access to object owner or admin users.

    For objects with a 'user' or 'owner' attribute.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff or request.user.is_superuser:
            return True

        owner = getattr(obj, "user", None) or getattr(obj, "owner", None)
        return owner == request.user


class CanManageUsers(HasResourcePermission):
    """Permission to manage users (create, update, delete)."""

    resource = "users"
    action_permission = "manage"


class CanViewUsers(HasResourcePermission):
    """Permission to view users."""

    resource = "users"
    action_permission = "view"


class CanManageRoles(HasResourcePermission):
    """Permission to manage roles (assign, remove)."""

    resource = "roles"
    action_permission = "manage"


class CanAssignRoles(HasResourcePermission):
    """Permission to assign roles to users."""

    resource = "roles"
    action_permission = "assign"
