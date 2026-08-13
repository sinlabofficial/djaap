"""Comprehensive API tests for authentication, user management, and role management."""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import Permission, Role, User, UserRole


@pytest.fixture
def api_client():
    """Provide APIClient for testing."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def create_user():
    """Factory for creating test users."""

    def _create_user(email, password="testpass123", **kwargs):
        user = User.objects.create(email=email, **kwargs)
        user.set_password(password)
        user.save()
        return user

    return _create_user


@pytest.fixture
def create_admin(create_user):
    """Factory for creating admin users."""

    def _create_admin(email="admin@example.com", **kwargs):
        return create_user(email, is_staff=True, **kwargs)

    return _create_admin


@pytest.fixture
def create_role():
    """Factory for creating roles."""

    def _create_role(name, level=10, **kwargs):
        existing = Role.all_objects.filter(name=name).first()
        if existing:
            if existing.deleted:
                existing.undelete()
            return existing
        return Role.objects.create(name=name, level=level, **kwargs)

    return _create_role


@pytest.fixture
def create_permission():
    """Factory for creating permissions."""

    def _create_permission(resource, action, **kwargs):
        existing = Permission.all_objects.filter(
            resource=resource, action=action
        ).first()
        if existing:
            if existing.deleted:
                existing.undelete()
            return existing
        return Permission.objects.create(resource=resource, action=action, **kwargs)

    return _create_permission


@pytest.fixture
def auth_headers():
    """Factory for generating auth headers."""

    def _auth_headers(user):
        refresh = RefreshToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}

    return _auth_headers


@pytest.mark.django_db
class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_login_with_email_success(self, api_client, create_user):
        """Test successful login with email."""
        create_user(
            "login@example.com", phone="+1234567890", employee_id="EMP001"
        )
        url = reverse("api:login")

        response = api_client.post(
            url, {"identifier": "login@example.com", "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert response.data["user"]["email"] == "login@example.com"

    def test_login_with_phone_success(self, api_client, create_user):
        """Test successful login with phone number."""
        create_user("phone@example.com", phone="+1234567890")
        url = reverse("api:login")

        response = api_client.post(
            url, {"identifier": "+1234567890", "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_login_with_employee_id_success(self, api_client, create_user):
        """Test successful login with employee_id."""
        create_user("emp@example.com", employee_id="EMP123")
        url = reverse("api:login")

        response = api_client.post(
            url, {"identifier": "EMP123", "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_login_invalid_credentials(self, api_client, create_user):
        """Test login with invalid credentials."""
        create_user("wrong@example.com")
        url = reverse("api:login")

        response = api_client.post(
            url, {"identifier": "wrong@example.com", "password": "wrongpassword"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.data

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent user."""
        url = reverse("api:login")

        response = api_client.post(
            url, {"identifier": "nonexistent@example.com", "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, api_client, create_user):
        """Test login with inactive user."""
        create_user("inactive@example.com", is_active=False)
        url = reverse("api:login")

        response = api_client.post(
            url, {"identifier": "inactive@example.com", "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, api_client):
        """Test login with missing required fields."""
        url = reverse("api:login")

        response = api_client.post(url, {"identifier": "test@example.com"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_success(self, api_client, create_user, auth_headers):
        """Test successful logout."""
        user = create_user("logout@example.com")
        url = reverse("api:logout")
        headers = auth_headers(user)

        refresh = RefreshToken.for_user(user)
        response = api_client.post(url, {"refresh": str(refresh)}, **headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Successfully logged out."

    def test_logout_without_token(self, api_client, create_user, auth_headers):
        """Test logout without providing refresh token."""
        user = create_user("logout2@example.com")
        url = reverse("api:logout")
        headers = auth_headers(user)

        response = api_client.post(url, **headers)

        assert response.status_code == status.HTTP_200_OK

    def test_logout_unauthenticated(self, api_client):
        """Test logout without authentication."""
        url = reverse("api:logout")

        response = api_client.post(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_success(self, api_client, create_user):
        """Test successful token refresh."""
        user = create_user("refresh@example.com")
        url = reverse("api:token_refresh")

        refresh = RefreshToken.for_user(user)
        response = api_client.post(url, {"refresh": str(refresh)})

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "message" in response.data

    def test_refresh_token_invalid(self, api_client):
        """Test refresh with invalid token."""
        url = reverse("api:token_refresh")

        response = api_client.post(url, {"refresh": "invalid-token"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_endpoint_success(self, api_client, create_user, auth_headers):
        """Test /me endpoint returns current user info."""
        user = create_user("me@example.com", phone="+1234567890", employee_id="EMP999")
        url = reverse("api:me")
        headers = auth_headers(user)

        response = api_client.get(url, **headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "me@example.com"
        assert response.data["phone"] == "+1234567890"
        assert response.data["employee_id"] == "EMP999"

    def test_me_endpoint_unauthenticated(self, api_client):
        """Test /me endpoint without authentication."""
        url = reverse("api:me")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserManagementEndpoints:
    """Tests for user management CRUD endpoints."""

    @pytest.fixture(autouse=True)
    def setup_permissions(self, create_permission, create_role):
        """Setup permissions for user management."""
        view_perm = create_permission("users", "view")
        manage_perm = create_permission("users", "manage")
        self.admin_role = create_role("Admin", level=100)
        self.admin_role.permissions.add(view_perm, manage_perm)

    def test_list_users_success(
        self, api_client, create_user, create_admin, auth_headers
    ):
        """Test listing users with proper permissions."""
        admin = create_admin("admin1@example.com")
        UserRole.objects.create(user=admin, role=self.admin_role, assigned_by=admin)
        create_user("user1@example.com")
        create_user("user2@example.com")

        url = reverse("api:user-list")
        headers = auth_headers(admin)

        response = api_client.get(url, **headers)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) >= 3

    def test_list_users_unauthorized(self, api_client, create_user, auth_headers):
        """Test listing users without proper permissions."""
        user = create_user("noperms@example.com")
        url = reverse("api:user-list")
        headers = auth_headers(user)

        response = api_client.get(url, **headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_users_unauthenticated(self, api_client):
        """Test listing users without authentication."""
        url = reverse("api:user-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_users_with_filters(
        self, api_client, create_user, create_admin, auth_headers
    ):
        """Test listing users with filters."""
        admin = create_admin("admin2@example.com")
        UserRole.objects.create(user=admin, role=self.admin_role, assigned_by=admin)
        create_user("filtered@example.com", is_staff=True)
        create_user("regular@example.com")

        url = reverse("api:user-list")
        headers = auth_headers(admin)

        response = api_client.get(url, {"is_staff": "true"}, **headers)

        assert response.status_code == status.HTTP_200_OK
        for user in response.data["results"]:
            assert user["is_staff"] is True

    def test_create_user_success(self, api_client, create_admin, auth_headers):
        """Test creating a new user."""
        admin = create_admin("admin3@example.com")
        UserRole.objects.create(user=admin, role=self.admin_role, assigned_by=admin)
        url = reverse("api:user-list")
        headers = auth_headers(admin)

        response = api_client.post(
            url,
            {
                "email": "newuser@example.com",
                "password": "newpass123",
                "password_confirm": "newpass123",
                "phone": "+1234567890",
                "employee_id": "NEW001",
            },
            **headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "newuser@example.com"
        assert response.data["phone"] == "+1234567890"

    def test_create_user_password_mismatch(
        self, api_client, create_admin, auth_headers
    ):
        """Test creating user with password mismatch."""
        admin = create_admin("admin4@example.com")
        UserRole.objects.create(user=admin, role=self.admin_role, assigned_by=admin)
        url = reverse("api:user-list")
        headers = auth_headers(admin)

        response = api_client.post(
            url,
            {
                "email": "baduser@example.com",
                "password": "pass123",
                "password_confirm": "different123",
            },
            **headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_user_detail_success(
        self, api_client, create_user, create_admin, auth_headers
    ):
        """Test getting user details."""
        admin = create_admin("admin5@example.com")
        UserRole.objects.create(user=admin, role=self.admin_role, assigned_by=admin)
        user = create_user("detail@example.com")

        url = reverse("api:user-detail", kwargs={"pk": user.id})
        headers = auth_headers(admin)

        response = api_client.get(url, **headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "detail@example.com"

    def test_get_user_detail_not_found(self, api_client, create_admin, auth_headers):
        """Test getting non-existent user details."""
        admin = create_admin("admin6@example.com")
        UserRole.objects.create(user=admin, role=self.admin_role, assigned_by=admin)

        url = reverse(
            "api:user-detail", kwargs={"pk": "12345678-1234-1234-1234-123456789abc"}
        )
        headers = auth_headers(admin)

        response = api_client.get(url, **headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_user_success(
        self, api_client, create_user, create_admin, auth_headers
    ):
        """Test updating user information."""
        admin = create_admin("admin7@example.com")
        UserRole.objects.create(user=admin, role=self.admin_role, assigned_by=admin)
        user = create_user("update@example.com", phone="+1111111111")

        url = reverse("api:user-detail", kwargs={"pk": user.id})
        headers = auth_headers(admin)

        response = api_client.patch(
            url,
            {
                "phone": "+9999999999",
                "employee_id": "UPDATED001",
            },
            **headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] == "+9999999999"
        assert response.data["employee_id"] == "UPDATED001"

    def test_delete_user_success(
        self, api_client, create_user, create_admin, auth_headers
    ):
        """Test soft deleting a user."""
        admin = create_admin("admin8@example.com")
        UserRole.objects.create(user=admin, role=self.admin_role, assigned_by=admin)
        user = create_user("delete@example.com")

        url = reverse("api:user-detail", kwargs={"pk": user.id})
        headers = auth_headers(admin)

        response = api_client.delete(url, **headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        user = User.all_objects.get(id=user.id)
        assert user.deleted is not None


@pytest.mark.django_db
class TestRoleManagementEndpoints:
    """Tests for role management endpoints."""

    @pytest.fixture(autouse=True)
    def setup_permissions(self, create_permission, create_role):
        """Setup permissions for role management."""
        assign_perm = create_permission("roles", "assign")
        self.manager_role = create_role("Manager", level=50)
        self.manager_role.permissions.add(assign_perm)
        self.regular_role = create_role("Staff", level=10)

    def test_list_roles_success(self, api_client, create_user, auth_headers):
        """Test listing roles."""
        user = create_user("roles@example.com")
        url = reverse("api:role-list")
        headers = auth_headers(user)

        response = api_client.get(url, **headers)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_assign_role_success(
        self, api_client, create_user, create_admin, auth_headers
    ):
        """Test assigning a role to a user."""
        admin = create_admin("admin9@example.com")
        UserRole.objects.create(user=admin, role=self.manager_role, assigned_by=admin)
        user = create_user("assign@example.com")

        url = reverse("api:user-assign-role", kwargs={"pk": user.id})
        headers = auth_headers(admin)

        response = api_client.post(
            url, {"role_id": str(self.regular_role.id)}, **headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["role"]["name"] == "Staff"

    def test_assign_role_already_assigned(
        self, api_client, create_user, create_admin, auth_headers
    ):
        """Test assigning already assigned role."""
        admin = create_admin("admin10@example.com")
        UserRole.objects.create(user=admin, role=self.manager_role, assigned_by=admin)
        user = create_user("already@example.com")
        UserRole.objects.create(user=user, role=self.regular_role, assigned_by=admin)

        url = reverse("api:user-assign-role", kwargs={"pk": user.id})
        headers = auth_headers(admin)

        response = api_client.post(
            url, {"role_id": str(self.regular_role.id)}, **headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already assigned" in response.data["detail"].lower()

    def test_assign_role_invalid_role(
        self, api_client, create_user, create_admin, auth_headers
    ):
        """Test assigning non-existent role."""
        admin = create_admin("admin11@example.com")
        UserRole.objects.create(user=admin, role=self.manager_role, assigned_by=admin)
        user = create_user("invalidrole@example.com")

        url = reverse("api:user-assign-role", kwargs={"pk": user.id})
        headers = auth_headers(admin)

        response = api_client.post(
            url, {"role_id": "12345678-1234-1234-1234-123456789abc"}, **headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_role_success(
        self, api_client, create_user, create_admin, auth_headers
    ):
        """Test removing a role from a user."""
        admin = create_admin("admin12@example.com")
        UserRole.objects.create(user=admin, role=self.manager_role, assigned_by=admin)
        user = create_user("remove@example.com")
        UserRole.objects.create(user=user, role=self.regular_role, assigned_by=admin)

        url = reverse(
            "api:user-remove-role",
            kwargs={"pk": user.id, "role_id": str(self.regular_role.id)},
        )
        headers = auth_headers(admin)

        response = api_client.delete(url, **headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserRole.objects.filter(user=user, role=self.regular_role).exists()

    def test_remove_role_not_assigned(
        self, api_client, create_user, create_admin, auth_headers
    ):
        """Test removing role that is not assigned."""
        admin = create_admin("admin13@example.com")
        UserRole.objects.create(user=admin, role=self.manager_role, assigned_by=admin)
        user = create_user("notassigned@example.com")

        url = reverse(
            "api:user-remove-role",
            kwargs={"pk": user.id, "role_id": str(self.regular_role.id)},
        )
        headers = auth_headers(admin)

        response = api_client.delete(url, **headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_role_without_permission(
        self, api_client, create_user, auth_headers
    ):
        """Test assigning role without proper permission."""
        user = create_user("noperms2@example.com")
        target_user = create_user("target@example.com")

        url = reverse("api:user-assign-role", kwargs={"pk": target_user.id})
        headers = auth_headers(user)

        response = api_client.post(
            url, {"role_id": str(self.regular_role.id)}, **headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_success(self, api_client):
        """Test health check endpoint."""
        url = reverse("api:health_check")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"


@pytest.mark.django_db
class TestLoginRateLimiting:
    """Tests for login rate limiting."""

    def test_login_rate_limit_after_5_attempts(self, api_client, create_user):
        """Test that login is rate limited after 5 attempts."""
        from rest_framework.test import APIClient

        create_user("ratelimit@example.com")
        url = reverse("api:login")

        responses = []
        for _i in range(7):
            client = APIClient()
            response = client.post(
                url,
                {"identifier": "ratelimit@example.com", "password": "wrongpassword"},
            )
            responses.append(response.status_code)

        assert status.HTTP_429_TOO_MANY_REQUESTS in responses


@pytest.mark.django_db
class TestUserRolesInResponse:
    """Tests for user roles in API responses."""

    def test_user_roles_in_me_response(
        self, api_client, create_user, create_role, auth_headers
    ):
        """Test that user roles are included in /me response."""
        user = create_user("rolesme@example.com")
        role = create_role("Developer", level=30)
        UserRole.objects.create(user=user, role=role, assigned_by=user)

        url = reverse("api:me")
        headers = auth_headers(user)

        response = api_client.get(url, **headers)

        assert response.status_code == status.HTTP_200_OK
        assert "roles" in response.data
        assert len(response.data["roles"]) == 1
        assert response.data["roles"][0]["name"] == "Developer"

    def test_user_roles_in_list_response(
        self,
        api_client,
        create_user,
        create_role,
        create_admin,
        create_permission,
        auth_headers,
    ):
        """Test that user roles are included in user list response."""
        view_perm = create_permission("users", "view")
        admin_role = create_role("AdminUser", level=100)
        admin_role.permissions.add(view_perm)

        admin = create_admin("adminroles@example.com")
        UserRole.objects.create(user=admin, role=admin_role, assigned_by=admin)

        user = create_user("withroles@example.com")
        role = create_role("Tester", level=20)
        UserRole.objects.create(user=user, role=role, assigned_by=admin)

        url = reverse("api:user-list")
        headers = auth_headers(admin)

        response = api_client.get(url, **headers)

        assert response.status_code == status.HTTP_200_OK
        user_data = next(
            u for u in response.data["results"] if u["email"] == "withroles@example.com"
        )
        assert "roles" in user_data
        assert len(user_data["roles"]) == 1
        assert user_data["roles"][0]["name"] == "Tester"


@pytest.mark.django_db
class TestAPIIntegration:
    """Integration tests for complete API workflows."""

    def test_complete_auth_flow(self, api_client, create_user):
        """Test complete authentication flow: login -> me -> logout."""
        create_user("flow@example.com")

        login_url = reverse("api:login")
        login_response = api_client.post(
            login_url, {"identifier": "flow@example.com", "password": "testpass123"}
        )
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        me_url = reverse("api:me")
        me_response = api_client.get(
            me_url, HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.data["email"] == "flow@example.com"

        logout_url = reverse("api:logout")
        logout_response = api_client.post(
            logout_url,
            {"refresh": refresh_token},
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        assert logout_response.status_code == status.HTTP_200_OK

    def test_complete_user_lifecycle(
        self, api_client, create_admin, create_permission, create_role, auth_headers
    ):
        """Test complete user lifecycle: create -> update -> assign role -> delete."""
        view_perm = create_permission("users", "view")
        manage_perm = create_permission("users", "manage")
        assign_perm = create_permission("roles", "assign")
        admin_role = create_role("SuperAdmin", level=100)
        admin_role.permissions.add(view_perm, manage_perm, assign_perm)

        admin = create_admin("lifecycle@example.com")
        UserRole.objects.create(user=admin, role=admin_role, assigned_by=admin)
        headers = auth_headers(admin)

        create_url = reverse("api:user-list")
        create_response = api_client.post(
            create_url,
            {
                "email": "lifecycleuser@example.com",
                "password": "lifepass123",
                "password_confirm": "lifepass123",
            },
            **headers,
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        user_id = create_response.data["id"]

        update_url = reverse("api:user-detail", kwargs={"pk": user_id})
        update_response = api_client.patch(
            update_url,
            {
                "phone": "+1234567890",
            },
            **headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["phone"] == "+1234567890"

        staff_role = create_role("StaffMember", level=10)
        assign_url = reverse("api:user-assign-role", kwargs={"pk": user_id})
        assign_response = api_client.post(
            assign_url, {"role_id": str(staff_role.id)}, **headers
        )
        assert assign_response.status_code == status.HTTP_201_CREATED

        delete_url = reverse("api:user-detail", kwargs={"pk": user_id})
        delete_response = api_client.delete(delete_url, **headers)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
