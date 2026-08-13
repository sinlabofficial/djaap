from typing import Any

from auditlog.models import LogEntry
from django.db import transaction

from .models import OrganizationSettings, Permission, PresentationMode, Role, User

_UNSET = object()


@transaction.atomic
def example_create(*, name: str, description: str = "") -> dict[str, Any]:
    """
    Example service function demonstrating the service layer pattern.

    Services should:
    - Use @transaction.atomic decorator
    - Accept keyword-only arguments
    - Return the created/updated object or relevant data
    - Have type hints
    - Follow naming convention: {model}_{action}
    """
    return {"id": 1, "name": name, "description": description}


@transaction.atomic
def example_update(*, instance_id: int, name: str | None = None) -> dict[str, Any]:
    """Example update service."""
    return {"id": instance_id, "name": name}


@transaction.atomic
def example_delete(*, instance_id: int) -> bool:
    """Example delete service."""
    return True


@transaction.atomic
def user_create(
    *,
    email: str,
    phone: str | None = None,
    employee_id: str | None = None,
    profile_name: str = "",
    is_staff: bool = False,
    is_active: bool = True,
    password: str,
) -> User:
    """Create an application user from validated dashboard input."""
    return User.objects.create_user(
        email=email,
        password=password,
        phone=phone,
        employee_id=employee_id,
        profile_name=profile_name,
        is_staff=is_staff,
        is_active=is_active,
    )


@transaction.atomic
def user_update(
    *,
    user: User,
    email: str | None | object = _UNSET,
    phone: str | None | object = _UNSET,
    employee_id: str | None | object = _UNSET,
    profile_name: str | object = _UNSET,
    is_staff: bool | None | object = _UNSET,
    is_active: bool | None | object = _UNSET,
    password: str | None = None,
) -> User:
    """Update application identity and access flags from validated input."""
    update_fields = ["updated"]
    if email is not _UNSET:
        user.email = email
        update_fields.append("email")
    if phone is not _UNSET:
        user.phone = phone
        update_fields.append("phone")
    if employee_id is not _UNSET:
        user.employee_id = employee_id
        update_fields.append("employee_id")
    if profile_name is not _UNSET:
        user.profile_name = str(profile_name)
        update_fields.append("profile_name")
    if is_staff is not _UNSET:
        user.is_staff = is_staff
        update_fields.append("is_staff")
    if is_active is not _UNSET:
        user.is_active = is_active
        update_fields.append("is_active")
    if password:
        user.set_password(password)
        update_fields.append("password")
    user.save(update_fields=update_fields)
    return user


@transaction.atomic
def user_delete(*, user: User) -> bool:
    """Soft-delete an application user."""
    if user.deleted is not None:
        return False
    user.delete()
    return True


@transaction.atomic
def role_create(
    *,
    name: str,
    level: int,
    description: str = "",
    presentation_mode_policy: str = PresentationMode.DEFAULT,
) -> Role:
    presentation_mode_policy = _validate_presentation_mode(
        presentation_mode_policy or PresentationMode.DEFAULT
    )
    return Role.objects.create(
        name=name.strip(),
        level=level,
        description=description.strip(),
        presentation_mode_policy=presentation_mode_policy,
    )


@transaction.atomic
def role_update(
    *,
    role: Role,
    name: str,
    level: int,
    description: str = "",
    presentation_mode_policy: str = PresentationMode.DEFAULT,
) -> Role:
    presentation_mode_policy = _validate_presentation_mode(
        presentation_mode_policy or role.presentation_mode_policy
    )
    role.name = name.strip()
    role.level = level
    role.description = description.strip()
    role.presentation_mode_policy = presentation_mode_policy
    role.save(
        update_fields=[
            "name",
            "level",
            "description",
            "presentation_mode_policy",
            "updated",
        ]
    )
    return role


@transaction.atomic
def role_delete(*, role: Role) -> None:
    role.delete()


@transaction.atomic
def permission_create(
    *, resource: str, action: str, description: str = ""
) -> Permission:
    return Permission.objects.create(
        resource=resource.strip(), action=action.strip(), description=description.strip()
    )


@transaction.atomic
def permission_update(
    *, permission: Permission, resource: str, action: str, description: str = ""
) -> Permission:
    permission.resource = resource.strip()
    permission.action = action.strip()
    permission.description = description.strip()
    permission.save(update_fields=["resource", "action", "description", "updated"])
    return permission


@transaction.atomic
def permission_delete(*, permission: Permission) -> None:
    permission.delete()


@transaction.atomic
def assign_permission_to_role(*, role: Role, permission: Permission) -> None:
    role.permissions.add(permission)


@transaction.atomic
def remove_permission_from_role(*, role: Role, permission: Permission) -> None:
    role.permissions.remove(permission)


def check_user_permission(user, resource: str, action: str) -> bool:
    """Check if user has permission for a resource and action.

    This service checks permissions based on user's roles.
    Uses union approach: if user has ANY role with the permission, returns True.

    Args:
        user: The user to check permissions for
        resource: The resource being accessed (e.g., "users", "items")
        action: The action being performed (e.g., "create", "update", "delete")

    Returns:
        bool: True if user has permission, False otherwise
    """
    from .models import UserRole

    # Superusers have all permissions
    if user.is_superuser:
        return True

    # Get all roles for the user
    user_roles = UserRole.objects.filter(user=user).select_related("role")

    # Check if any role has the required permission
    for user_role in user_roles:
        role = user_role.role
        # Check if this role has the permission
        has_perm = role.permissions.filter(resource=resource, action=action).exists()
        if has_perm:
            return True

    return False


def assign_role_to_user(*, user, role, assigned_by) -> bool:
    """Assign a role to a user.

    Args:
        user: The user to assign the role to
        role: The role to assign
        assigned_by: The user assigning the role (for audit)

    Returns:
        bool: True if role was assigned, False if already assigned
    """
    from .models import UserRole

    # Check if already assigned
    if UserRole.objects.filter(user=user, role=role).exists():
        return False

    UserRole.objects.create(user=user, role=role, assigned_by=assigned_by)
    return True


def remove_role_from_user(*, user, role) -> bool:
    """Remove a role from a user.

    Args:
        user: The user to remove the role from
        role: The role to remove

    Returns:
        bool: True if role was removed, False if not assigned
    """
    from .models import UserRole

    deleted, _ = UserRole.objects.filter(user=user, role=role).delete()
    return deleted > 0


@transaction.atomic
def user_update_profile(
    *,
    user,
    profile_name: str,
    profile_photo=None,
    password: str | None = None,
):
    """Update user-owned profile fields and optionally change the password."""
    old_photo = user.profile_photo
    user.profile_name = profile_name.strip()
    update_fields = ["profile_name", "updated"]

    if profile_photo is False:
        user.profile_photo = None
        update_fields.append("profile_photo")
    elif profile_photo is not None:
        user.profile_photo = profile_photo
        update_fields.append("profile_photo")

    if password:
        user.set_password(password)
        update_fields.append("password")

    user.save(update_fields=update_fields)

    if password:
        LogEntry.objects.log_create(
            user,
            action=LogEntry.Action.UPDATE,
            actor=user,
            changes={"profile": ["password changed"]},
        )

    if (
        profile_photo is not None
        and old_photo
        and old_photo.name != user.profile_photo.name
    ):
        old_photo.delete(save=False)

    return user


@transaction.atomic
def organization_settings_update(
    *,
    actor,
    organization_name: str,
    description: str = "",
    address: str = "",
    phone: str = "",
    email: str = "",
    logo=None,
) -> OrganizationSettings:
    """Create or update the singleton organization identity with an audit event."""
    organization, _ = OrganizationSettings.objects.get_or_create(key="default")
    old_logo = organization.logo
    old_values = {
        "organization_name": organization.organization_name,
        "description": organization.description,
        "address": organization.address,
        "phone": organization.phone,
        "email": organization.email,
        "logo": old_logo.name if old_logo else "",
    }

    organization.organization_name = organization_name.strip()
    organization.description = description.strip()
    organization.address = address.strip()
    organization.phone = phone.strip()
    organization.email = email.strip()
    if logo is False:
        organization.logo = None
    elif logo is not None:
        organization.logo = logo
    organization.save()

    new_values = {
        "organization_name": organization.organization_name,
        "description": organization.description,
        "address": organization.address,
        "phone": organization.phone,
        "email": organization.email,
        "logo": organization.logo.name if organization.logo else "",
    }
    changes = {
        field: [old_values[field], new_values[field]]
        for field in old_values
        if old_values[field] != new_values[field]
    }
    if changes:
        LogEntry.objects.log_create(
            organization,
            action=LogEntry.Action.UPDATE,
            actor=actor,
            changes=changes,
        )

    if (
        (logo is False or logo is not None)
        and old_logo
        and old_logo.name != (organization.logo.name if organization.logo else "")
    ):
        old_logo.delete(save=False)

    return organization


def _validate_presentation_mode(mode: str) -> str:
    valid_modes = {choice.value for choice in PresentationMode}
    if mode not in valid_modes:
        raise ValueError(f"Unsupported presentation mode: {mode}")
    return mode


@transaction.atomic
def organization_presentation_policy_update(
    *,
    actor: User,
    presentation_mode: str,
    mobile_presentation_enabled: bool,
) -> OrganizationSettings:
    """Update the organization presentation policy and record the decision."""
    mode = _validate_presentation_mode(presentation_mode)
    organization, _ = OrganizationSettings.objects.get_or_create(key="default")
    old_values = {
        "presentation_mode": organization.presentation_mode,
        "mobile_presentation_enabled": organization.mobile_presentation_enabled,
    }
    organization.presentation_mode = mode
    organization.mobile_presentation_enabled = mobile_presentation_enabled
    organization.save(
        update_fields=[
            "presentation_mode",
            "mobile_presentation_enabled",
            "updated",
        ]
    )
    new_values = {
        "presentation_mode": organization.presentation_mode,
        "mobile_presentation_enabled": organization.mobile_presentation_enabled,
    }
    changes = {
        field: [old_values[field], new_values[field]]
        for field in old_values
        if old_values[field] != new_values[field]
    }
    if changes:
        LogEntry.objects.log_create(
            organization,
            action=LogEntry.Action.UPDATE,
            actor=actor,
            changes=changes,
        )
    return organization


@transaction.atomic
def user_presentation_preference_update(
    *, user: User, presentation_mode: str
) -> User:
    """Update only the calling user's presentation preference."""
    mode = _validate_presentation_mode(presentation_mode)
    old_mode = user.presentation_mode
    user.presentation_mode = mode
    user.save(update_fields=["presentation_mode", "updated"])
    if old_mode != mode:
        LogEntry.objects.log_create(
            user,
            action=LogEntry.Action.UPDATE,
            actor=user,
            changes={"presentation_mode": [old_mode, mode]},
        )
    return user


@transaction.atomic
def role_presentation_policy_update(
    *, actor: User, role: Role, presentation_mode: str
) -> Role:
    """Set a forced role policy; ``default`` means no forced shell."""
    mode = _validate_presentation_mode(presentation_mode)
    old_mode = role.presentation_mode_policy
    role.presentation_mode_policy = mode
    role.save(update_fields=["presentation_mode_policy", "updated"])
    if old_mode != mode:
        LogEntry.objects.log_create(
            role,
            action=LogEntry.Action.UPDATE,
            actor=actor,
            changes={"presentation_mode_policy": [old_mode, mode]},
        )
    return role
