from .models import WebhookEvent


def webhook_event_get(*, event_id) -> WebhookEvent | None:
    """Return one webhook event through the public Platform Runtime read seam."""
    return WebhookEvent.objects.filter(id=event_id).first()
