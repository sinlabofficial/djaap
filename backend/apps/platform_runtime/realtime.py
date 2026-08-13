import hashlib
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from .models import RealtimeEvent, RuntimeLog
from .redaction import redact_value


@dataclass(frozen=True)
class RealtimeEnvelope:
    event_id: str
    event_type: str
    required_permission: str
    correlation_id: str | None
    safe_payload: Mapping[str, Any]
    published_at: datetime


def _redact(value: Any) -> Any:
    return redact_value(value)


def publish_realtime_event(
    *,
    event_type: str,
    payload: Mapping[str, Any],
    required_permission: str = "",
    correlation_id: str | None = None,
) -> RealtimeEvent:
    """Persist and publish a safe notification after the current transaction commits."""
    if not event_type or not event_type.strip():
        raise ValueError("event_type is required")
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    if required_permission and not re.fullmatch(
        r"[a-z][a-z0-9_]*:[a-z][a-z0-9_]*", required_permission
    ):
        raise ValueError("required_permission must use resource:action format")
    event = RealtimeEvent.objects.create(
        event_type=event_type.strip(),
        required_permission=required_permission.strip(),
        correlation_id=correlation_id,
        safe_payload=_redact(payload),
        expires_at=timezone.now() + timedelta(days=1),
    )
    transaction.on_commit(lambda: _dispatch_realtime_event(event.id))
    return event


def _dispatch_realtime_event(event_id) -> None:
    event = RealtimeEvent.objects.filter(id=event_id).first()
    if event is None:
        return
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            _group_name(event.required_permission),
            {
                "type": "realtime.event",
                "event": _envelope(event),
            },
        )
    except ImportError:
        # Channels is optional; HTTP polling remains the fallback.
        return
    except Exception as error:
        RuntimeLog.objects.create(
            task_result_id=f"realtime-{uuid.uuid4().hex}",
            task_name="platform_runtime.realtime",
            backend="channels",
            status=RuntimeLog.Status.FAILED,
            event_type="realtime.publish_failed",
            severity="error",
            correlation_id=event.correlation_id,
            safe_metadata={"error_class": f"{type(error).__module__}.{type(error).__qualname__}"},
        )


def _group_name(required_permission: str) -> str:
    if not required_permission:
        return "realtime-broadcast"
    digest = hashlib.sha256(required_permission.encode()).hexdigest()[:32]
    return f"realtime-permission-{digest}"


def _envelope(event: RealtimeEvent) -> dict[str, Any]:
    return {
        "event_id": str(event.id),
        "event_type": event.event_type,
        "correlation_id": event.correlation_id,
        "payload": event.safe_payload,
        "published_at": event.published_at.isoformat(),
    }


def realtime_events_since(*, since: datetime | None = None):
    queryset = RealtimeEvent.objects.filter(expires_at__gt=timezone.now()).order_by(
        "published_at"
    )
    if since:
        queryset = queryset.filter(published_at__gt=since)
    return queryset
