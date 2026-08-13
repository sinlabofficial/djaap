import pytest
from auditlog.models import LogEntry
from django.urls import reverse

from apps.core.models import Permission, Role, User, UserRole


@pytest.mark.django_db
def test_authenticated_user_sees_global_dashboard_summary_and_available_navigation(client):
    user = User.objects.create_user(
        email="member@example.com",
        password="testpass123",
    )
    Role.objects.create(name="Operator", level=10)
    client.force_login(user)

    response = client.get(reverse("dashboard:home"))

    assert response.status_code == 200
    assert b">Roles</p>" in response.content
    assert b'data-testid="summary-roles"' in response.content
    assert b">Users</p>" in response.content
    assert b'data-testid="summary-users"' in response.content
    assert b'data-testid="summary-active-users"' in response.content
    assert b'class="mt-2 text-3xl font-black text-on-surface">1</p>' in response.content
    assert b"href=\"#\"" not in response.content
    assert b"Workspace" not in response.content
    assert b"Permission groups" in response.content
    assert b"Accounts in this deployment" in response.content


@pytest.mark.django_db
def test_user_list_requires_session_but_all_members_can_read(client):
    user = User.objects.create_user(
        email="member@example.com",
        password="testpass123",
    )
    client.force_login(user)

    response = client.get(reverse("dashboard:user_list"))

    assert response.status_code == 200

    client.logout()
    anonymous_response = client.get(reverse("dashboard:user_list"))

    assert anonymous_response.status_code == 302
    assert "/dashboard/login/" in anonymous_response["Location"]


@pytest.mark.django_db
def test_staff_user_create_and_edit_use_global_dashboard_flow(client):
    staff = User.objects.create_user(
        email="admin@example.com",
        password="testpass123",
        is_staff=True,
    )
    client.force_login(staff)

    create_response = client.post(
        reverse("dashboard:user_create"),
        {
            "email": "new-user@example.com",
            "password": "newpass123",
            "password_confirm": "newpass123",
            "is_active": "on",
        },
    )
    created = User.objects.get(email="new-user@example.com")

    assert create_response.status_code == 200
    assert created.check_password("newpass123")

    edit_response = client.post(
        reverse("dashboard:user_edit", kwargs={"user_id": created.id}),
        {
            "email": "updated-user@example.com",
            "password": "updatedpass123",
            "password_confirm": "updatedpass123",
            "is_active": "on",
        },
    )
    created.refresh_from_db()

    assert edit_response.status_code == 200
    assert created.email == "updated-user@example.com"
    assert created.check_password("updatedpass123")


@pytest.mark.django_db
def test_staff_can_manage_roles_permissions_and_assign_permissions(client):
    staff = User.objects.create_user(
        email="admin@example.com",
        password="testpass123",
        is_staff=True,
    )
    client.force_login(staff)

    role_response = client.post(
        reverse("dashboard:role_create"),
        {"name": "Manager", "level": 50, "description": "Managers"},
    )
    role = Role.objects.get(name="Manager")

    permission_response = client.post(
        reverse("dashboard:permission_create"),
        {
            "resource": "reports",
            "action": "view",
            "description": "View reports",
        },
    )
    permission = Permission.objects.get(resource="reports", action="view")

    assign_response = client.post(
        reverse("dashboard:role_permission_assign", kwargs={"role_id": role.id}),
        {"permission": permission.id},
    )
    role.refresh_from_db()

    assert role_response.status_code == 200
    assert permission_response.status_code == 200
    assert assign_response.status_code == 204
    assert role.permissions.filter(id=permission.id).exists()

    edit_role_response = client.post(
        reverse("dashboard:role_edit", kwargs={"role_id": role.id}),
        {"name": "Senior Manager", "level": 60, "description": "Updated"},
    )
    edit_permission_response = client.post(
        reverse(
            "dashboard:permission_edit", kwargs={"permission_id": permission.id}
        ),
        {
            "resource": "reports",
            "action": "export",
            "description": "Export reports",
        },
    )
    remove_response = client.post(
        reverse(
            "dashboard:role_permission_remove",
            kwargs={"role_id": role.id, "permission_id": permission.id},
        )
    )
    delete_permission_response = client.post(
        reverse(
            "dashboard:permission_delete", kwargs={"permission_id": permission.id}
        )
    )
    role.refresh_from_db()
    permission.refresh_from_db()

    assert edit_role_response.status_code == 200
    assert edit_permission_response.status_code == 200
    assert remove_response.status_code == 204
    assert delete_permission_response.status_code == 204
    assert role.name == "Senior Manager"
    assert permission.deleted is not None
    assert LogEntry.objects.filter(object_pk=str(role.id)).exists()
    assert LogEntry.objects.filter(object_pk=str(permission.id)).exists()

    delete_role_response = client.post(
        reverse("dashboard:role_delete", kwargs={"role_id": role.id})
    )
    assert delete_role_response.status_code == 204
    assert Role.deleted_objects.filter(id=role.id).exists()


@pytest.mark.django_db
def test_regular_user_cannot_mutate_roles_or_permissions(client):
    user = User.objects.create_user(
        email="member@example.com",
        password="testpass123",
    )
    client.force_login(user)

    response = client.post(
        reverse("dashboard:role_create"),
        {"name": "Blocked", "level": 10},
    )

    assert response.status_code == 302
    assert "/dashboard/login/" in response["Location"]
    assert not Role.objects.filter(name="Blocked").exists()


@pytest.mark.django_db
def test_role_permission_grants_dashboard_mutation_without_staff_flag(client):
    user = User.objects.create_user(
        email="manager@example.com",
        password="testpass123",
    )
    access_role = Role.objects.create(name="Access Manager", level=80)
    manage_permission = Permission.objects.create(resource="roles", action="manage")
    access_role.permissions.add(manage_permission)
    UserRole.objects.create(user=user, role=access_role, assigned_by=user)
    client.force_login(user)

    response = client.post(
        reverse("dashboard:role_create"),
        {"name": "Granted", "level": 10},
    )

    assert response.status_code == 200
    assert Role.objects.filter(name="Granted").exists()
