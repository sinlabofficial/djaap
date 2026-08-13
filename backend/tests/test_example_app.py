import pytest
from django.test import Client
from django.urls import reverse

from apps.core.models import Permission, Role, User, UserRole
from apps.example.models import Item
from apps.example.selectors import item_get, item_list
from apps.example.services import item_create, item_delete, item_update


@pytest.mark.django_db
class TestItemModel:
    """Tests for Item model."""

    def test_item_creation(self):
        """Test creating an item."""
        item = Item.objects.create(name="Test Item", description="Test Description")
        assert item.name == "Test Item"
        assert item.description == "Test Description"
        assert item.is_active is True

    def test_item_str(self):
        """Test item string representation."""
        item = Item.objects.create(name="Test Item")
        assert str(item) == "Test Item"


@pytest.mark.django_db
class TestItemServices:
    """Tests for Item services (TDD)."""

    def test_item_create(self):
        """Test item_create service."""
        item = item_create(name="Service Item", description="Created via service")
        assert item.name == "Service Item"
        assert Item.objects.count() == 1

    def test_item_update(self):
        """Test item_update service."""
        item = item_create(name="Original")
        updated = item_update(item_id=str(item.id), name="Updated")
        assert updated.name == "Updated"

    def test_item_delete(self):
        """Test item_delete service."""
        item = item_create(name="To Delete")
        result = item_delete(item_id=str(item.id))
        assert result is True
        assert item_list().count() == 0
        item.refresh_from_db()
        assert item.is_active is False


@pytest.mark.django_db
class TestItemSelectors:
    """Tests for Item selectors."""

    def test_item_list(self):
        """Test item_list selector."""
        item_create(name="Item 1")
        item_create(name="Item 2")
        items = item_list()
        assert items.count() == 2

    def test_item_list_with_filter(self):
        """Test item_list with filters."""
        item_create(name="Active Item", is_active=True)
        item_create(name="Inactive Item", is_active=False)
        active_items = item_list(filters={"is_active": True})
        assert active_items.count() == 1

    def test_item_get(self):
        """Test item_get selector."""
        item = item_create(name="Get Me")
        found = item_get(item_id=str(item.id))
        assert found is not None
        assert found.name == "Get Me"

    def test_item_get_not_found(self):
        """Test item_get with non-existent ID."""
        result = item_get(item_id="12345678-1234-1234-1234-123456789abc")
        assert result is None


@pytest.mark.django_db
class TestItemViews:
    def setup_method(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            email="example-admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff)

    """Tests for Item views (Integration tests)."""

    def test_list_view(self):
        """Test item list view."""
        item_create(name="View Item")
        response = self.client.get(reverse("example:list"))
        assert response.status_code == 200
        assert b"View Item" in response.content

    def test_create_view(self):
        """Test item create view."""
        data = {"name": "New Item", "description": "New Description"}
        response = self.client.post(reverse("example:create"), data)
        assert response.status_code == 302
        assert Item.objects.count() == 1

    def test_detail_view(self):
        """Test item detail view."""
        item = item_create(name="Detail Item")
        response = self.client.get(reverse("example:detail", kwargs={"pk": str(item.id)}))
        assert response.status_code == 200
        assert b"Detail Item" in response.content

    def test_create_view_get(self):
        """Test item create view GET request."""
        response = self.client.get(reverse("example:create"))
        assert response.status_code == 200
        assert b'data-testid="example-item-form"' in response.content
        assert b"Item details" in response.content
        assert b"What should this item be called?" in response.content
        assert b"Describe the purpose or context for this item." in response.content

    def test_update_view_get(self):
        """Test item update view GET request."""
        item = item_create(name="Update Item")
        response = self.client.get(reverse("example:update", kwargs={"pk": str(item.id)}))
        assert response.status_code == 200

    def test_update_view_post(self):
        """Test item update view POST request."""
        item = item_create(name="Original Name")
        data = {"name": "Updated Name", "description": "Updated Description"}
        response = self.client.post(
            reverse("example:update", kwargs={"pk": str(item.id)}),
            data
        )
        assert response.status_code == 302
        item.refresh_from_db()
        assert item.name == "Updated Name"

    def test_delete_view_post(self):
        """Test item delete view POST request."""
        item = item_create(name="Delete Item")
        response = self.client.post(reverse("example:delete", kwargs={"pk": str(item.id)}))
        assert response.status_code == 302
        assert item_list().count() == 0

    def test_anonymous_user_is_redirected_from_example(self):
        self.client.logout()

        response = self.client.get(reverse("example:list"))

        assert response.status_code == 302
        assert "/dashboard/login/" in response["Location"]

    def test_role_permission_can_manage_example(self):
        self.client.logout()
        user = User.objects.create_user(
            email="example-manager@example.com",
            password="testpass123",
        )
        role = Role.objects.create(name="Example Manager", level=20)
        permission = Permission.objects.create(resource="example", action="manage")
        role.permissions.add(permission)
        UserRole.objects.create(user=user, role=role, assigned_by=user)
        self.client.force_login(user)

        response = self.client.post(
            reverse("example:create"),
            {"name": "Managed Item", "description": "Created by permission"},
        )

        assert response.status_code == 302
        assert Item.objects.filter(name="Managed Item").exists()
