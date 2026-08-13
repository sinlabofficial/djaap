from datetime import timedelta

import pytest
from auditlog.models import LogEntry
from django.utils import timezone

from apps.core.models import User
from apps.platform_runtime.maintenance import cleanup_expired_runtime_data
from apps.platform_runtime.models import RealtimeEvent, RuntimeLog, WebhookEvent


def make_webhook(event_id="event-1"):
    return WebhookEvent.objects.create(
        provider="billing",
        event_type="invoice.updated",
        external_event_id=event_id,
        dedupe_key=f"dedupe-{event_id}",
        payload_hash="a" * 64,
        payload_reference=f"sha256:{event_id}",
        safe_payload={"access_token": "secret-value", "id": event_id},
        safe_metadata={"api_key": "provider-secret"},
    )


@pytest.mark.django_db
def test_runtime_storage_redaction_and_structured_log(caplog):
    with caplog.at_level("INFO", logger="apps.platform_runtime"):
        log = RuntimeLog.objects.create(
            task_result_id="result-safe",
            task_name="apps.example.tasks.sync_item",
            backend="default",
            status=RuntimeLog.Status.FAILED,
            safe_metadata={
                "password": "secret-value",
                "nested": {"authorization": "Bearer secret-token"},
                "reason": "temporary failure",
            },
        )

    log.refresh_from_db()
    assert log.safe_metadata == {
        "password": "[REDACTED]",
        "nested": {"authorization": "[REDACTED]"},
        "reason": "temporary failure",
    }
    assert caplog.records[-1].platform_runtime_event["status"] == "failed"
    assert "secret-value" not in caplog.text
    assert "secret-token" not in caplog.text

    webhook = make_webhook()
    realtime = RealtimeEvent.objects.create(
        event_type="order.updated",
        safe_payload={"token": "secret-value", "id": "order-1"},
    )
    webhook.refresh_from_db()
    realtime.refresh_from_db()
    assert webhook.safe_payload["access_token"] == "[REDACTED]"
    assert webhook.safe_metadata["api_key"] == "[REDACTED]"
    assert realtime.safe_payload["token"] == "[REDACTED]"


@pytest.mark.django_db
def test_cleanup_removes_expired_runtime_data_but_preserves_audit_log():
    actor = User.objects.create_user(email="operator@example.com")
    old_time = timezone.now() - timedelta(days=31)
    runtime_log = RuntimeLog.objects.create(
        task_result_id="expired-result",
        task_name="apps.example.tasks.sync_item",
        backend="default",
        status=RuntimeLog.Status.SUCCEEDED,
    )
    RuntimeLog.objects.filter(id=runtime_log.id).update(created=old_time)
    webhook = make_webhook(event_id="expired-webhook")
    WebhookEvent.objects.filter(id=webhook.id).update(received_at=old_time, created=old_time)
    realtime = RealtimeEvent.objects.create(event_type="expired.event")
    RealtimeEvent.objects.filter(id=realtime.id).update(
        created=old_time, published_at=old_time, expires_at=old_time
    )
    LogEntry.objects.log_create(
        webhook,
        action=LogEntry.Action.CREATE,
        actor=actor,
    )
    audit_entry = LogEntry.objects.latest("timestamp")

    result = cleanup_expired_runtime_data()

    assert result == {"runtime_logs": 1, "webhook_events": 1, "realtime_events": 1}
    assert not RuntimeLog.objects.filter(id=runtime_log.id).exists()
    assert not WebhookEvent.objects.filter(id=webhook.id).exists()
    assert not RealtimeEvent.objects.filter(id=realtime.id).exists()
    assert LogEntry.objects.filter(id=audit_entry.id).exists()
