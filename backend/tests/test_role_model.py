"""
Tests for Role model - TDD RED phase.

These tests should FAIL initially because the Role model is not yet implemented.

Role Hierarchy:
- Owner: 100
- Admin: 80
- Manager: 60
- Operator: 40
- Staff: 20
"""

import pytest
from django.db import IntegrityError

from apps.core.models import Role


@pytest.mark.django_db
class TestRoleModel:
    """Test Role model behavior."""

    def test_role_creation(self):
        """Test creating a role."""
        role = Role.objects.create(
            name="Admin", level=80, description="Administrator role"
        )
        assert role.name == "Admin"
        assert role.level == 80
        assert role.description == "Administrator role"

    def test_role_name_unique(self):
        """Test that role name must be unique."""
        Role.objects.create(name="Manager", level=60)
        with pytest.raises(IntegrityError):
            Role.objects.create(name="Manager", level=60)

    def test_role_str_representation(self):
        """Test Role string representation."""
        role = Role.objects.create(name="Operator", level=40)
        assert str(role) == "Operator"

    def test_role_level_validation(self):
        """Test role level must be positive."""
        with pytest.raises((IntegrityError, ValueError)):
            Role.objects.create(name="Invalid", level=-1)

    def test_role_hierarchy_comparison(self):
        """Test comparing roles by level."""
        admin = Role.objects.create(name="Admin", level=80)
        manager = Role.objects.create(name="Manager", level=60)

        assert admin.level > manager.level
        assert admin.has_higher_rank_than(manager)

    def test_role_predefined_levels(self):
        """Test predefined role levels."""
        owner = Role.objects.create(name="Owner", level=100)
        admin = Role.objects.create(name="Admin", level=80)
        manager = Role.objects.create(name="Manager", level=60)
        operator = Role.objects.create(name="Operator", level=40)
        staff = Role.objects.create(name="Staff", level=20)

        assert owner.level == 100
        assert admin.level == 80
        assert manager.level == 60
        assert operator.level == 40
        assert staff.level == 20
