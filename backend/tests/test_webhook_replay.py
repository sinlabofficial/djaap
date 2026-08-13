from unittest.mock import patch

import pytest
from auditlog.models import LogEntry
from django.urls import reverse

from apps.core.models import Permission, Role, User, UserRole
from apps.platform_runtime.models import RuntimeLog, WebhookEvent
from apps.platform_runtime.webhooks import replay_webhook_event


def failed_event() -> WebhookEvent:
    return WebhookEvent.objects.create(
        provider="billing",
        event_type="invoice.created",
        external_event_id="evt-failed",
        dedupe_key="failed-event-key",
        payload_hash="a" * 64,
        payload_reference="sha256:" + "a" * 64,
        safe_payload={"id": "evt-failed", "token": "[REDACTED]"},
        correlation_id="corr-failed",
        status=WebhookEvent.Status.FAILED,
    )


@pytest.mark.django_db(transaction=True)
def test_replay_creates_new_event_with_idempotency_and_audit_log():
    actor = User.objects.create_user(email="operator@example.com", password="testpass123")
    event = failed_event()

    with patch("apps.platform_runtime.webhooks.process_webhook_event.enqueue") as enqueue:
        replay = replay_webhook_event(event=event, actor=actor)

    assert replay.replay_of_id == event.id
    assert replay.dedupe_key != event.dedupe_key
    assert replay.safe_payload["token"] == "[REDACTED]"
    enqueue.assert_called_once()
    assert RuntimeLog.objects.filter(
        event_type="webhook.replayed", safe_metadata__event_id=str(replay.id)
    ).exists()
    assert LogEntry.objects.filter(object_pk=str(replay.id)).exists()


@pytest.mark.django_db
def test_replay_only_allows_failed_event():
    actor = User.objects.create_user(email="operator@example.com", password="testpass123")
    event = failed_event()
    event.status = WebhookEvent.Status.PROCESSED
    event.save(update_fields=["status", "updated"])

    with pytest.raises(ValueError):
        replay_webhook_event(event=event, actor=actor)


@pytest.mark.django_db(transaction=True)
def test_repeated_replay_command_returns_existing_replay():
    actor = User.objects.create_user(email="operator@example.com", password="testpass123")
    event = failed_event()
    with patch("apps.platform_runtime.webhooks.process_webhook_event.enqueue"):
        first = replay_webhook_event(event=event, actor=actor)
        second = replay_webhook_event(event=event, actor=actor)

    assert first.id == second.id
    assert WebhookEvent.objects.filter(replay_of=event).count() == 1


@pytest.mark.django_db
def test_webhook_dashboard_filters_and_replay_requires_permission(client):
    user = User.objects.create_user(email="operator@example.com", password="testpass123")
    event = failed_event()
    RuntimeLog.objects.create(
        task_result_id="webhook-failed-log",
        task_name="webhook:billing",
        backend="webhook",
        status=RuntimeLog.Status.FAILED,
        event_type="webhook.failed",
        severity="error",
        correlation_id="corr-failed",
        safe_metadata={
            "provider": "billing",
            "external_event_id": "evt-failed",
            "event_id": str(event.id),
        },
    )
    client.force_login(user)
    logs_url = reverse("dashboard:logs") + "?tab=webhooks&provider=billing&status=failed&severity=error"

    view_permission = Permission.objects.create(resource="runtime_logs", action="view")
    view_role = Role.objects.create(name="Runtime viewer", level=10)
    view_role.permissions.add(view_permission)
    UserRole.objects.create(user=user, role=view_role)

    assert client.get(logs_url).status_code == 200
    logs_response = client.get(logs_url)
    assert b"evt-failed" in logs_response.content
    assert b">Replay<" not in logs_response.content
    denied = client.post(reverse("dashboard:webhook_replay", args=[event.id]))
    assert denied.status_code == 302
    assert denied.url.startswith("/dashboard/login/")
    assert WebhookEvent.objects.filter(replay_of=event).count() == 0

    permission = Permission.objects.create(resource="runtime_logs", action="replay")
    role = Role.objects.create(name="Replay operator", level=10)
    role.permissions.add(permission)
    UserRole.objects.create(user=user, role=role)

    with patch("apps.platform_runtime.webhooks.process_webhook_event.enqueue"):
        response = client.post(reverse("dashboard:webhook_replay", args=[event.id]))

    assert response.status_code == 302
    assert WebhookEvent.objects.filter(replay_of=event).count() == 1
