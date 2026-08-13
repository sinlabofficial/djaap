import hashlib
import hmac
import json
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from auditlog.models import LogEntry
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import RuntimeLog, WebhookEvent
from .redaction import is_sensitive_key, redact_value
from .tasks import platform_task

WebhookHandler = Callable[["WebhookEnvelope"], Any]


@dataclass(frozen=True)
class WebhookEnvelope:
    provider: str
    event_type: str
    external_event_id: str | None
    correlation_id: str | None
    payload_hash: str
    payload_reference: str
    safe_payload: Mapping[str, Any]
    event_id: str


@dataclass(frozen=True)
class WebhookProvider:
    secret: str
    handler: WebhookHandler


_providers: dict[str, WebhookProvider] = {}


def register_webhook_provider(provider: str, secret: str, handler: WebhookHandler) -> None:
    """Register a provider adapter owned by a Domain App."""
    if not provider or not secret:
        raise ValueError("provider and secret are required")
    _providers[provider] = WebhookProvider(secret=secret, handler=handler)


def _log_webhook(
    *,
    provider: str,
    event_type: str,
    correlation_id: str | None = None,
    external_event_id: str | None = None,
    reason: str | None = None,
    failed: bool = False,
    status: str | None = None,
    event_id: str | None = None,
) -> None:
    metadata: dict[str, str] = {"provider": provider}
    if external_event_id:
        metadata["external_event_id"] = external_event_id
    if reason:
        metadata["reason"] = reason
    if event_id:
        metadata["event_id"] = event_id
    RuntimeLog.objects.create(
        task_result_id=f"webhook-{uuid.uuid4().hex}",
        task_name=f"webhook:{provider}",
        backend="webhook",
        status=status or (RuntimeLog.Status.FAILED if failed else RuntimeLog.Status.QUEUED),
        event_type=event_type,
        severity="error" if failed else "info",
        correlation_id=correlation_id,
        safe_metadata=metadata,
        enqueued_at=timezone.now(),
    )


def _valid_signature(secret: str, body: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)


def _payload_value(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value):
            return str(value)
    return None


def _is_sensitive_key(key: str) -> bool:
    return is_sensitive_key(key)


def _redact_payload(value: Any) -> Any:
    return redact_value(value)


@platform_task(backend="webhook", retry_for=(TimeoutError,), max_attempts=3)
def process_webhook_event(event_id: str) -> None:
    event = WebhookEvent.objects.get(id=event_id)
    provider = _providers.get(event.provider)
    if provider is None:
        raise RuntimeError(f"Webhook provider is not registered: {event.provider}")

    envelope = WebhookEnvelope(
        provider=event.provider,
        event_type=event.event_type,
        external_event_id=event.external_event_id,
        correlation_id=event.correlation_id,
        payload_hash=event.payload_hash,
        payload_reference=event.payload_reference,
        safe_payload=event.safe_payload,
        event_id=str(event.id),
    )
    try:
        provider.handler(envelope)
    except Exception:
        WebhookEvent.objects.filter(id=event.id).update(
            status=WebhookEvent.Status.FAILED,
            safe_metadata={**event.safe_metadata, "dispatch_failed": True},
        )
        _log_webhook(
            provider=event.provider,
            event_type="webhook.failed",
            correlation_id=event.correlation_id,
            external_event_id=event.external_event_id,
            failed=True,
            event_id=str(event.id),
        )
        raise
    WebhookEvent.objects.filter(id=event.id).update(status=WebhookEvent.Status.PROCESSED)
    _log_webhook(
        provider=event.provider,
        event_type="webhook.processed",
        correlation_id=event.correlation_id,
        external_event_id=event.external_event_id,
        status=RuntimeLog.Status.SUCCEEDED,
        event_id=str(event.id),
    )


def receive_webhook(
    *,
    provider: str,
    body: bytes,
    signature: str,
    headers: Mapping[str, str],
) -> tuple[WebhookEvent | None, bool]:
    registered = _providers.get(provider)
    if registered is None:
        _log_webhook(provider=provider, event_type="webhook.rejected", reason="unknown_provider", failed=True)
        raise LookupError(provider)
    if not _valid_signature(registered.secret, body, signature):
        _log_webhook(provider=provider, event_type="webhook.rejected", reason="invalid_signature", failed=True)
        raise PermissionError("invalid webhook signature")

    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        _log_webhook(provider=provider, event_type="webhook.rejected", reason="invalid_json", failed=True)
        raise ValueError("invalid JSON payload") from error
    if not isinstance(payload, Mapping):
        _log_webhook(provider=provider, event_type="webhook.rejected", reason="object_required", failed=True)
        raise ValueError("JSON object payload is required")

    payload_hash = hashlib.sha256(body).hexdigest()
    external_id = _payload_value(payload, "event_id", "id")
    event_type = _payload_value(payload, "event_type", "type") or "webhook.received"
    correlation_id = headers.get("X-Correlation-ID") or external_id or payload_hash[:24]
    dedupe_key = hashlib.sha256(
        f"{provider}:event:{external_id}".encode() if external_id else f"{provider}:payload:{payload_hash}".encode()
    ).hexdigest()
    _log_webhook(
        provider=provider,
        event_type="webhook.received",
        correlation_id=correlation_id,
        external_event_id=external_id,
    )

    try:
        with transaction.atomic():
            event, created = WebhookEvent.objects.get_or_create(
                dedupe_key=dedupe_key,
                defaults={
                    "provider": provider,
                    "event_type": event_type,
                    "external_event_id": external_id,
                    "payload_hash": payload_hash,
                    "payload_reference": f"sha256:{payload_hash}",
                    "safe_payload": _redact_payload(payload),
                    "correlation_id": correlation_id,
                    "status": WebhookEvent.Status.VERIFIED,
                    "safe_metadata": {"provider": provider, "event_type": event_type},
                },
            )
            if not created:
                if event.status == WebhookEvent.Status.VERIFIED or (
                    event.status == WebhookEvent.Status.FAILED
                    and event.safe_metadata.get("dispatch_failed")
                ):
                    transaction.on_commit(lambda: _enqueue_webhook(event, dedupe_key, correlation_id))
                return event, True
            _log_webhook(
                provider=provider,
                event_type="webhook.verified",
                correlation_id=correlation_id,
                external_event_id=external_id,
                event_id=str(event.id),
            )
            transaction.on_commit(
                lambda: _enqueue_webhook(event, dedupe_key, correlation_id)
            )
    except IntegrityError:
        event = WebhookEvent.objects.get(dedupe_key=dedupe_key)
        return event, True
    return event, False


def _enqueue_webhook(event: WebhookEvent, dedupe_key: str, correlation_id: str) -> None:
    try:
        process_webhook_event.enqueue(
            str(event.id),
            idempotency_key=f"webhook:{dedupe_key}",
            correlation_id=correlation_id,
        )
    except Exception:
        WebhookEvent.objects.filter(id=event.id).update(
            status=WebhookEvent.Status.FAILED,
            safe_metadata={**event.safe_metadata, "dispatch_failed": True},
        )
        _log_webhook(
            provider=event.provider,
            event_type="webhook.enqueue_failed",
            correlation_id=correlation_id,
            external_event_id=event.external_event_id,
            failed=True,
            event_id=str(event.id),
        )
        raise
    # ImmediateBackend may finish the task before enqueue returns; never regress
    # a terminal processing state back to enqueued.
    WebhookEvent.objects.filter(
        id=event.id, status=WebhookEvent.Status.VERIFIED
    ).update(status=WebhookEvent.Status.ENQUEUED)
    _log_webhook(
        provider=event.provider,
        event_type="webhook.enqueued",
        correlation_id=correlation_id,
        external_event_id=event.external_event_id,
        event_id=str(event.id),
    )


@transaction.atomic
def replay_webhook_event(*, event: WebhookEvent, actor) -> WebhookEvent:
    """Create and enqueue one safe, idempotent replay of a failed event."""
    event = WebhookEvent.objects.select_for_update().get(id=event.id)
    if event.status == WebhookEvent.Status.REPLAYED:
        return WebhookEvent.objects.get(replay_of=event)
    if event.status != WebhookEvent.Status.FAILED:
        raise ValueError("Only failed webhook events can be replayed")

    replay = WebhookEvent.objects.create(
        provider=event.provider,
        event_type=event.event_type,
        external_event_id=event.external_event_id,
        dedupe_key=f"replay:{event.id}:{uuid.uuid4().hex}",
        payload_hash=event.payload_hash,
        payload_reference=event.payload_reference,
        safe_payload=event.safe_payload,
        correlation_id=event.correlation_id,
        status=WebhookEvent.Status.VERIFIED,
        replay_of=event,
    )
    event.status = WebhookEvent.Status.REPLAYED
    event.save(update_fields=["status", "updated"])
    _log_webhook(
        provider=replay.provider,
        event_type="webhook.replayed",
        correlation_id=replay.correlation_id,
        external_event_id=replay.external_event_id,
        event_id=str(replay.id),
    )
    LogEntry.objects.log_create(
        replay,
        action=LogEntry.Action.UPDATE,
        actor=actor,
        changes={"replay_of": [None, str(event.id)]},
    )
    transaction.on_commit(
        lambda: _enqueue_webhook(replay, replay.dedupe_key, replay.correlation_id or "")
    )
    return replay
