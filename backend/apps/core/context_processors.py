from django.urls import reverse

from .selectors import (
    organization_settings_get,
    presentation_mode_resolve,
    user_has_permission,
)


def organization(request):
    """Expose organization identity to shared dashboard layout templates."""
    organization_settings = organization_settings_get()
    if not getattr(request.user, "is_authenticated", False):
        return {"organization": organization_settings}

    decision = presentation_mode_resolve(
        user=request.user,
        organization=organization_settings,
    )
    can_view_logs = request.user.is_superuser or request.user.is_staff or user_has_permission(
        user=request.user,
        permission="runtime_logs:view",
    )
    navigation = [
        {
            "label": "Dashboard",
            "url": reverse("dashboard:home"),
            "icon": "layout-dashboard",
            "prefix": "/dashboard/",
            "exact": True,
        },
        {
            "label": "Example Items",
            "url": reverse("example:list"),
            "icon": "package",
            "prefix": "/dashboard/example/",
        },
        {
            "label": "Profile",
            "url": reverse("dashboard:profile"),
            "icon": "user",
            "prefix": "/dashboard/profile/",
        },
    ]
    if can_view_logs:
        navigation.insert(
            2,
            {
                "label": "Logs",
                "url": reverse("dashboard:logs"),
                "icon": "scroll-text",
                "prefix": "/dashboard/logs/",
            },
        )
    more_navigation = []
    if request.user.is_staff or request.user.is_superuser:
        more_navigation.append(
            {
                "label": "Settings",
                "url": reverse("dashboard:settings"),
                "icon": "settings",
                "prefix": "/dashboard/settings/",
            }
        )
    for item in navigation:
        item["active"] = (
            request.path == item["prefix"]
            if item.get("exact")
            else request.path.startswith(item["prefix"])
        )
    for item in more_navigation:
        item["active"] = request.path.startswith(item["prefix"])
    mobile_navigation_columns = (
        5 if more_navigation else 4 if len(navigation) == 4 else 3
    )
    return {
        "organization": organization_settings,
        "presentation_mode": decision.mode,
        "presentation_mode_source": decision.source,
        "mobile_navigation": navigation[:4],
        "mobile_more_navigation": more_navigation,
        "mobile_navigation_columns": mobile_navigation_columns,
    }
