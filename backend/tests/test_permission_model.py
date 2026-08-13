"""
Tests for Permission model - TDD RED phase.

Permissions define what actions can be performed on resources.
Example: resource="users", action="create"
"""

import pytest
from django.db import IntegrityError

from apps.core.models import Permission


@pytest.mark.django_db
class TestPermissionModel:
    """Test Permission model behavior."""

    def test_permission_creation(self):
        """Test creating a permission."""
        perm = Permission.objects.create(
            resource="users", action="create", description="Can create users"
        )
        assert perm.resource == "users"
        assert perm.action == "create"
        assert perm.description == "Can create users"

    def test_permission_unique_together(self):
        """Test that resource+action combination must be unique."""
        Permission.objects.create(resource="users", action="delete")
        with pytest.raises(IntegrityError):
            Permission.objects.create(resource="users", action="delete")

    def test_permission_str_representation(self):
        """Test Permission string representation."""
        perm = Permission.objects.create(resource="items", action="update")
        assert str(perm) == "items:update"

    def test_permission_multiple_actions_per_resource(self):
        """Test that same resource can have different actions."""
        perm1 = Permission.objects.create(resource="users", action="create")
        perm2 = Permission.objects.create(resource="users", action="update")
        perm3 = Permission.objects.create(resource="users", action="delete")

        assert perm1.resource == perm2.resource == perm3.resource
        assert perm1.action != perm2.action != perm3.action

    def test_permission_different_resources_same_action(self):
        """Test that different resources can have same action."""
        perm1 = Permission.objects.create(resource="users", action="view")
        perm2 = Permission.objects.create(resource="items", action="view")

        assert perm1.resource != perm2.resource
        assert perm1.action == perm2.action
