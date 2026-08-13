from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import RealtimeEvent, RuntimeLog, WebhookEvent


def cleanup_expired_runtime_data(*, now=None, retention_days: int | None = None) -> dict[str, int]:
    """Delete expired operational data without touching Audit Log records."""
    current_time = now or timezone.now()
    days = (
        settings.PLATFORM_RUNTIME_RETENTION_DAYS
        if retention_days is None
        else retention_days
    )
    cutoff = current_time - timedelta(days=days)
    runtime_deleted, _ = RuntimeLog.objects.filter(created__lt=cutoff).delete()
    webhook_deleted, _ = WebhookEvent.objects.filter(received_at__lt=cutoff).delete()
    realtime_deleted, _ = RealtimeEvent.objects.filter(published_at__lt=cutoff).delete()
    return {
        "runtime_logs": runtime_deleted,
        "webhook_events": webhook_deleted,
        "realtime_events": realtime_deleted,
    }
