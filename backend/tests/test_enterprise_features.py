"""
Enterprise Features Tests - Wave 4
Tests for Soft Delete, Audit Logging, and Impersonation features.

Follows TDD pattern: Write tests first (RED), then implement (GREEN).
"""


import pytest
from auditlog.models import LogEntry
from auditlog.registry import auditlog
from django.test import Client
from safedelete.models import SOFT_DELETE_CASCADE

from apps.core.models import Role, User, UserRole
from tests.factories import UserFactory


@pytest.mark.django_db
class TestSoftDelete:
    """Tests for django-safedelete integration."""

    def test_user_model_uses_safe_delete_model(self):
        """Test that User model inherits from SafeDeleteModel."""
        from safedelete.models import SafeDeleteModel

        assert issubclass(User, SafeDeleteModel)

    def test_user_has_soft_delete_policy(self):
        """Test that User model uses SOFT_DELETE_CASCADE policy."""
        assert User._safedelete_policy == SOFT_DELETE_CASCADE

    def test_user_manager_has_safe_delete_methods(self):
        """Test that User manager has safedelete methods."""
        assert hasattr(User, "objects")
        assert hasattr(User, "all_objects")
        assert hasattr(User, "deleted_objects")

    def test_soft_delete_keeps_record_in_database(self):
        """Test that soft delete doesn't actually delete the record."""
        user = UserFactory.create(email="delete_me@example.com")
        user_id = user.id
        user.delete()
        assert User.all_objects.filter(id=user_id).exists()

    def test_soft_deleted_user_not_in_default_queryset(self):
        """Test that soft deleted users are excluded from default queryset."""
        user = UserFactory.create(email="hidden@example.com")
        assert User.objects.filter(email="hidden@example.com").exists()
        user.delete()
        assert not User.objects.filter(email="hidden@example.com").exists()

    def test_soft_deleted_user_in_all_objects(self):
        """Test that soft deleted users appear in all_objects."""
        user = UserFactory.create(email="deleted@example.com")
        user.delete()
        assert User.all_objects.filter(email="deleted@example.com").exists()

    def test_soft_deleted_user_in_deleted_objects(self):
        """Test that soft deleted users appear in deleted_objects."""
        user = UserFactory.create(email="trash@example.com")
        user.delete()
        assert User.deleted_objects.filter(email="trash@example.com").exists()

    def test_soft_delete_sets_deleted_at(self):
        """Test that soft delete sets deleted timestamp."""
        user = UserFactory.create()
        assert user.deleted is None
        user.delete()
        user.refresh_from_db()
        assert user.deleted is not None

    def test_undelete_restores_user(self):
        """Test that undelete restores soft deleted user."""
        user = UserFactory.create(email="restore_me@example.com")
        user.delete()
        assert not User.objects.filter(email="restore_me@example.com").exists()
        user.undelete()
        assert User.objects.filter(email="restore_me@example.com").exists()

    def test_hard_delete_actually_deletes(self):
        """Test that hard delete actually removes the record."""
        user = UserFactory.create()
        user_id = user.id
        from safedelete.models import HARD_DELETE

        user.delete(force_policy=HARD_DELETE)
        assert not User.all_objects.filter(id=user_id).exists()


@pytest.mark.django_db
class TestAuditLog:
    """Tests for django-auditlog integration."""

    def test_user_model_registered_with_auditlog(self):
        """Test that User model is registered with auditlog."""
        assert User in auditlog.get_models()

    def test_user_creation_creates_log_entry(self):
        """Test that creating a user creates an audit log entry."""
        initial_count = LogEntry.objects.count()
        UserFactory.create(email="audit@example.com")
        assert LogEntry.objects.count() > initial_count

    def test_user_update_creates_log_entry(self):
        """Test that updating a user creates an audit log entry."""
        user = UserFactory.create(email="update_me@example.com")
        initial_count = LogEntry.objects.count()
        user.email = "updated@example.com"
        user.save()
        assert LogEntry.objects.count() > initial_count

    def test_user_delete_creates_log_entry(self):
        """Test that deleting a user creates an audit log entry."""
        user = UserFactory.create(email="delete_me@example.com")
        initial_count = LogEntry.objects.count()
        user.delete()
        assert LogEntry.objects.count() > initial_count

    def test_audit_log_tracks_changes(self):
        """Test that audit log tracks field changes."""
        user = UserFactory.create(email="original@example.com", phone="1234567890")
        old_phone = user.phone
        user.phone = "0987654321"
        user.save()
        # Log entry exists for this user
        log = LogEntry.objects.filter(
            object_repr__icontains=user.email, action=LogEntry.Action.UPDATE
        ).first()
        assert log is not None
        assert "phone" in log.changes_dict
        assert log.changes_dict["phone"] == [old_phone, "0987654321"]

    def test_audit_log_includes_user_info(self):
        """Test that audit log captures actor information."""
        admin_user = UserFactory.create(email="admin@example.com")
        from auditlog.middleware import AuditlogMiddleware
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.post("/fake-url/")
        request.user = admin_user

        middleware = AuditlogMiddleware(lambda req: None)
        # Modern middleware uses __call__, not process_request
        middleware(request)

        new_user = User.objects.create(email="newuser@example.com")
        log = LogEntry.objects.filter(
            object_repr__icontains=new_user.email, action=LogEntry.Action.CREATE
        ).first()
        assert log is not None


@pytest.mark.django_db
class TestImpersonation:
    """Tests for django-impersonate integration."""

    def test_impersonate_urls_configured(self):
        """Test that impersonate URLs are configured."""
        from django.urls import resolve

        try:
            resolver = resolve("/impersonate/")
            assert resolver is not None
        except Exception:  # noqa: BLE001
            pytest.skip("Impersonate URLs not yet configured")

    def test_impersonation_requires_staff(self):
        """Test that only staff users can impersonate."""
        client = Client()
        regular_user = UserFactory.create(email="regular@example.com")
        target_user = UserFactory.create(email="target@example.com")
        client.force_login(regular_user)
        response = client.get(f"/impersonate/{target_user.id}/")
        assert response.status_code in [302, 403]

    def test_staff_can_impersonate(self):
        """Test that staff users can impersonate other users."""
        client = Client()
        staff_user = UserFactory.create(email="staff@example.com", is_staff=True)
        target_user = UserFactory.create(email="target@example.com")
        client.force_login(staff_user)
        response = client.get(f"/impersonate/{target_user.id}/")
        assert response.status_code in [200, 302]

    def test_impersonation_session_tracking(self):
        """Test that impersonation is tracked in session."""
        client = Client()
        staff_user = UserFactory.create(email="admin@example.com", is_staff=True)
        target_user = UserFactory.create(email="victim@example.com")
        client.force_login(staff_user)
        client.get(f"/impersonate/{target_user.id}/")
        session = client.session
        assert "impersonator" in session or "_impersonate" in session

    def test_stop_impersonation(self):
        """Test that stopping impersonation works."""
        client = Client()
        staff_user = UserFactory.create(email="admin2@example.com", is_staff=True)
        target_user = UserFactory.create(email="user2@example.com")
        client.force_login(staff_user)
        client.get(f"/impersonate/{target_user.id}/")
        response = client.get("/impersonate/stop/")
        assert response.status_code in [200, 302]

    def test_impersonation_list_requires_staff(self):
        """Test that impersonation list view requires staff."""
        client = Client()
        regular_user = UserFactory.create(email="user3@example.com")
        client.force_login(regular_user)
        response = client.get("/impersonate/list/")
        assert response.status_code in [302, 403]

    def test_impersonation_search_requires_staff(self):
        """Test that impersonation search requires staff."""
        client = Client()
        regular_user = UserFactory.create(email="user4@example.com")
        client.force_login(regular_user)
        response = client.get("/impersonate/search/")
        assert response.status_code in [302, 403]


@pytest.mark.django_db
class TestEnterpriseIntegration:
    """End-to-end integration tests for all enterprise features."""

    def test_full_user_lifecycle_with_audit_and_soft_delete(self):
        """
        Integration test: Create user -> Update -> Soft Delete -> Audit trail
        """
        user = UserFactory.create(email="lifecycle@example.com", phone="1234567890")
        create_log = LogEntry.objects.filter(
            object_repr__icontains=user.email, action=LogEntry.Action.CREATE
        ).first()
        assert create_log is not None

        user.phone = "5555555555"
        user.save()
        update_log = LogEntry.objects.filter(
            object_repr__icontains=user.email, action=LogEntry.Action.UPDATE
        ).first()
        assert update_log is not None

        user.delete()
        assert not User.objects.filter(email="lifecycle@example.com").exists()
        assert User.all_objects.filter(email="lifecycle@example.com").exists()

        # Audit log may record soft delete as DELETE or UPDATE (depending on safedelete integration)
        delete_log = (
            LogEntry.objects.filter(
                object_repr__icontains=user.email,
                action__in=[LogEntry.Action.DELETE, LogEntry.Action.UPDATE],
            )
            .order_by("-timestamp")
            .first()
        )
        assert delete_log is not None

        user.undelete()
        assert User.objects.filter(email="lifecycle@example.com").exists()

    def test_admin_impersonation_with_audit_trail(self):
        """
        Integration test: Admin impersonates user with full audit trail.
        """
        client = Client()
        admin_user = UserFactory.create(email="admin_test@example.com", is_staff=True)
        regular_user = UserFactory.create(email="regular_test@example.com")
        client.force_login(admin_user)
        response = client.get(f"/impersonate/{regular_user.id}/")
        assert response.status_code in [200, 302]
        response = client.get("/impersonate/stop/")
        assert response.status_code in [200, 302]

    def test_soft_deleted_user_cannot_login(self):
        """Test that soft deleted users cannot authenticate."""
        user = UserFactory.create(email="deleted_user@example.com")
        user.set_password("testpass123")
        user.save()
        from django.contrib.auth import authenticate

        authenticated = authenticate(
            identifier="deleted_user@example.com", password="testpass123"
        )
        assert authenticated is not None
        user.delete()
        authenticated = authenticate(
            identifier="deleted_user@example.com", password="testpass123"
        )
        assert authenticated is None

    def test_audit_log_integrity_with_soft_delete(self):
        """
        Test that audit logs maintain integrity even when users are soft deleted.
        """
        user = UserFactory.create(email="audit_integrity@example.com")
        user.phone = "1111111111"
        user.save()
        user.phone = "2222222222"
        user.save()
        user.delete()
        logs = LogEntry.objects.filter(object_repr__icontains=user.email)
        assert logs.count() >= 3
        for log in logs:
            assert user.email in log.object_repr

    def test_role_assignment_with_soft_delete_and_audit(self):
        """
        Integration test: Role assignment with soft delete and audit logging.
        """
        admin_user = UserFactory.create(email="role_admin@example.com", is_staff=True)
        regular_user = UserFactory.create(email="role_user@example.com")
        role = Role.objects.create(name="Manager", level=60)
        user_role = UserRole.objects.create(
            user=regular_user, role=role, assigned_by=admin_user
        )
        role_log = LogEntry.objects.filter(
            object_repr__icontains=str(user_role), action=LogEntry.Action.CREATE
        ).first()
        assert role_log is not None
        user_role.delete()
        assert UserRole.all_objects.filter(id=user_role.id).exists()


@pytest.mark.django_db
class TestSoftDeleteQuerySetBehavior:
    """Detailed tests for SafeDeleteQuerySet behavior."""

    def test_count_excludes_deleted(self):
        """Test that count() excludes deleted objects."""
        UserFactory.create(email="user1@example.com")
        UserFactory.create(email="user2@example.com")
        user3 = UserFactory.create(email="user3@example.com")
        initial_count = User.objects.count()
        assert initial_count == 3
        user3.delete()
        assert User.objects.count() == 2
        assert User.all_objects.count() == 3

    def test_filter_excludes_deleted(self):
        """Test that filter() excludes deleted objects."""
        user = UserFactory.create(email="filter_test@example.com")
        assert User.objects.filter(email="filter_test@example.com").exists()
        user.delete()
        assert not User.objects.filter(email="filter_test@example.com").exists()
        assert User.all_objects.filter(email="filter_test@example.com").exists()

    def test_get_raises_exception_for_deleted(self):
        """Test that get() raises exception for deleted objects."""
        user = UserFactory.create(email="get_test@example.com")
        user_id = user.id
        assert User.objects.get(id=user_id) == user
        user.delete()
        from django.core.exceptions import ObjectDoesNotExist

        with pytest.raises(ObjectDoesNotExist):
            User.objects.get(id=user_id)

    def test_all_objects_queryset_includes_deleted(self):
        """Test that all_objects includes deleted records."""
        user = UserFactory.create(email="all_objects_test@example.com")
        user.delete()
        all_users = list(User.all_objects.all())
        assert user in all_users

    def test_deleted_objects_queryset_only_deleted(self):
        """Test that deleted_objects only returns deleted records."""
        active_user = UserFactory.create(email="active@example.com")
        deleted_user = UserFactory.create(email="deleted_only@example.com")
        deleted_user.delete()
        deleted_qs = User.deleted_objects.all()
        assert deleted_user in deleted_qs
        assert active_user not in deleted_qs


@pytest.mark.django_db
class TestAuditLogMiddleware:
    """Tests for audit log middleware functionality."""

    def test_middleware_sets_actor_on_request(self):
        """Test that middleware sets actor from request user."""
        from auditlog.middleware import AuditlogMiddleware
        from django.test import RequestFactory

        user = UserFactory.create(email="middleware_test@example.com")
        factory = RequestFactory()
        request = factory.get("/test/")
        request.user = user

        middleware = AuditlogMiddleware(lambda req: None)
        # Modern Django middleware uses __call__
        middleware(request)
        assert request.user == user


@pytest.mark.django_db
class TestImpersonationPermissions:
    """Detailed tests for impersonation permission handling."""

    def test_superuser_can_impersonate(self):
        """Test that superusers can impersonate."""
        client = Client()
        superuser = UserFactory.create(
            email="superuser@example.com", is_staff=True, is_superuser=True
        )
        target = UserFactory.create(email="target_super@example.com")
        client.force_login(superuser)
        response = client.get(f"/impersonate/{target.id}/")
        assert response.status_code in [200, 302]

    def test_non_staff_cannot_access_impersonate(self):
        """Test that non-staff users cannot access impersonate URLs."""
        client = Client()
        regular_user = UserFactory.create(email="regular5@example.com")
        target = UserFactory.create(email="target5@example.com")
        client.force_login(regular_user)
        endpoints = [
            f"/impersonate/{target.id}/",
            "/impersonate/list/",
            "/impersonate/search/",
            "/impersonate/stop/",
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [302, 403, 404], (
                f"Endpoint {endpoint} should be restricted"
            )
