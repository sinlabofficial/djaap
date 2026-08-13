from typing import Any

from django.db.models import QuerySet

from .models import Item


def item_list(*, filters: dict[str, Any] | None = None) -> QuerySet[Item]:
    """Get active items with optional filtering."""
    queryset = Item.objects.all()

    if filters:
        if "is_active" in filters:
            queryset = queryset.filter(is_active=filters["is_active"])
        if "search" in filters:
            queryset = queryset.filter(name__icontains=filters["search"])
        else:
            queryset = queryset.filter(is_active=True)
    else:
        queryset = queryset.filter(is_active=True)

    return queryset


def item_get(*, item_id: str) -> Item | None:
    """Get an active item by ID."""
    try:
        return Item.objects.get(id=item_id, is_active=True)
    except Item.DoesNotExist:
        return None
