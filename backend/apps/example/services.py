
from django.db import transaction

from .models import Item


@transaction.atomic
def item_create(*, name: str, description: str = "", is_active: bool = True) -> Item:
    """Create a new item."""
    return Item.objects.create(
        name=name,
        description=description.strip(),
        is_active=is_active
    )


@transaction.atomic
def item_update(
    *, item_id: str, name: str | None = None, description: str | None = None
) -> Item:
    """Update an existing item."""
    item = Item.objects.get(id=item_id)
    if name is not None:
        item.name = name.strip()
    if description is not None:
        item.description = description.strip()
    item.save(update_fields=["name", "description", "updated"])
    return item


@transaction.atomic
def item_delete(*, item_id: str) -> bool:
    """Safely remove an item from normal application reads."""
    item = Item.objects.filter(id=item_id, is_active=True).first()
    if item is None:
        return False
    item.is_active = False
    item.save(update_fields=["is_active", "updated"])
    return True
