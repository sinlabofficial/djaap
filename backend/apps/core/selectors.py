from dataclasses import dataclass
from typing import Any

from .models import OrganizationSettings, PresentationMode, Role, User, UserRole

PRESENTATION_MODE_DEFAULT = PresentationMode.DEFAULT
PRESENTATION_MODE_DASHBOARD = PresentationMode.DASHBOARD
PRESENTATION_MODE_MOBILE = PresentationMode.MOBILE


@dataclass(frozen=True)
class PresentationModeDecision:
    mode: str
    source: str
    forced: bool = False


def presentation_mode_resolve(
    *,
    user: User,
    organization: OrganizationSettings | None = None,
    feature_enabled: bool | None = None,
) -> PresentationModeDecision:
    """Resolve the presentation shell without changing business capability.

    The order is intentionally centralized and deterministic:
    forced role policy -> user preference -> organization default.
    """
    if organization is None:
        organization = organization_settings_get()

    enabled = (
        organization.mobile_presentation_enabled
        if feature_enabled is None and organization is not None
        else bool(feature_enabled)
    )
    if not enabled:
        return PresentationModeDecision(
            mode=PRESENTATION_MODE_DASHBOARD,
            source="dashboard_default",
        )

    forced_role = (
        UserRole.objects.filter(
            user=user,
            deleted__isnull=True,
            role__deleted__isnull=True,
            role__presentation_mode_policy__in=(
                PRESENTATION_MODE_DASHBOARD,
                PRESENTATION_MODE_MOBILE,
            ),
        )
        .select_related("role")
        .order_by("-role__level")
        .first()
    )
    if forced_role is not None:
        return PresentationModeDecision(
            mode=forced_role.role.presentation_mode_policy,
            source="role_policy",
            forced=True,
        )

    if user.presentation_mode in (PRESENTATION_MODE_DASHBOARD, PRESENTATION_MODE_MOBILE):
        return PresentationModeDecision(
            mode=user.presentation_mode,
            source="user_preference",
        )

    organization_mode = (
        organization.presentation_mode
        if organization is not None
        else PRESENTATION_MODE_DASHBOARD
    )
    if organization_mode == PRESENTATION_MODE_MOBILE:
        return PresentationModeDecision(
            mode=PRESENTATION_MODE_MOBILE,
            source="organization_default",
        )
    return PresentationModeDecision(
        mode=PRESENTATION_MODE_DASHBOARD,
        source="organization_default",
    )


def organization_settings_get() -> OrganizationSettings | None:
    """Return the configured organization identity, if one exists."""
    return OrganizationSettings.objects.first()


def example_list(*, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Example selector function demonstrating the selector layer pattern.

    Selectors should:
    - Be read-only (no mutations)
    - Accept keyword-only arguments
    - Return QuerySet or list of data
    - Have type hints
    - Follow naming convention: {model}_{action}
    """
    return []


def example_get(*, instance_id: int) -> dict[str, Any] | None:
    """Example get selector."""
    return None


def example_filter(*, search: str = "") -> list[dict[str, Any]]:
    """Example filter selector."""
    return []


def user_profile_get(*, user):
    """Return the active profile for the authenticated user."""
    from .models import User

    return User.objects.filter(id=user.id, deleted__isnull=True).first()


def users_list(*, filters: dict[str, Any] | None = None):
    """Return active users for external adapters and platform reads."""
    queryset = User.objects.filter(deleted__isnull=True)
    filters = filters or {}
    if filters.get("email"):
        queryset = queryset.filter(email__icontains=filters["email"])
    if "is_staff" in filters:
        queryset = queryset.filter(is_staff=filters["is_staff"])
    if "is_active" in filters:
        queryset = queryset.filter(is_active=filters["is_active"])
    return queryset.order_by("-created")


def roles_list():
    """Return active roles for external adapters and platform reads."""
    return Role.objects.filter(deleted__isnull=True).order_by("-level")


def role_get(*, role_id):
    """Return one active role by identifier."""
    return Role.objects.filter(id=role_id, deleted__isnull=True).first()


def user_role_get(*, user: User, role: Role):
    """Return an active role assignment for a user."""
    return UserRole.objects.filter(
        user=user,
        role=role,
        deleted__isnull=True,
    ).select_related("role").first()


def user_has_permission(*, user: User, permission: str) -> bool:
    """Return whether a user has an active resource:action permission."""
    if user.is_superuser:
        return True

    resource, action = permission.split(":", 1)
    return UserRole.objects.filter(
        user=user,
        deleted__isnull=True,
        role__deleted__isnull=True,
        role__permissions__resource=resource,
        role__permissions__action=action,
        role__permissions__deleted__isnull=True,
    ).exists()
