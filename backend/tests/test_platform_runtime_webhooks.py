import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from django.test import Client

from apps.platform_runtime.models import RuntimeLog, WebhookEvent
from apps.platform_runtime.webhooks import register_webhook_provider


def signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.mark.django_db(transaction=True)
def test_inbound_webhook_verifies_persists_without_raw_payload_and_enqueues():
    body = json.dumps(
        {
            "type": "invoice.created",
            "id": "evt-1",
            "token": "secret",
            "client_secret": "client-secret",
            "nested": {"access_token": "access-secret", "display": "safe"},
        }
    ).encode()
    handled = []
    register_webhook_provider("test-valid", "provider-secret", handled.append)

    response = Client().post(
        "/webhooks/test-valid/",
        data=body,
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE=signature("provider-secret", body),
        HTTP_X_CORRELATION_ID="corr-1",
    )

    assert response.status_code == 202
    event = WebhookEvent.objects.get(provider="test-valid")
    assert event.external_event_id == "evt-1"
    assert event.payload_reference == f"sha256:{hashlib.sha256(body).hexdigest()}"
    assert not hasattr(event, "payload")
    assert len(handled) == 1
    assert handled[0].payload_reference == event.payload_reference
    assert handled[0].safe_payload["token"] == "[REDACTED]"
    assert handled[0].safe_payload["client_secret"] == "[REDACTED]"
    assert handled[0].safe_payload["nested"]["access_token"] == "[REDACTED]"
    assert RuntimeLog.objects.filter(event_type__in=[
        "webhook.received", "webhook.verified", "webhook.enqueued"
    ]).count() == 3
    assert all("provider-secret" not in str(log.safe_metadata) for log in RuntimeLog.objects.all())
    assert all("secret" not in str(log.safe_metadata) for log in RuntimeLog.objects.all())


@pytest.mark.django_db(transaction=True)
def test_invalid_signature_is_rejected_before_event_persistence():
    body = b'{"id":"evt-rejected"}'
    register_webhook_provider("test-rejected", "provider-secret", lambda envelope: None)

    response = Client().post(
        "/webhooks/test-rejected/",
        data=body,
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE="sha256=invalid",
    )

    assert response.status_code == 401
    assert not WebhookEvent.objects.filter(provider="test-rejected").exists()
    log = RuntimeLog.objects.get(event_type="webhook.rejected")
    assert log.status == RuntimeLog.Status.FAILED
    assert log.safe_metadata == {"provider": "test-rejected", "reason": "invalid_signature"}


@pytest.mark.django_db(transaction=True)
def test_webhook_deduplicates_by_provider_and_external_id():
    body = b'{"type":"invoice.created","id":"evt-duplicate"}'
    handled = []
    register_webhook_provider("test-dedupe", "provider-secret", handled.append)

    for _ in range(2):
        response = Client().post(
            "/webhooks/test-dedupe/",
            data=body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=signature("provider-secret", body),
        )
        assert response.status_code == 202

    assert WebhookEvent.objects.filter(provider="test-dedupe").count() == 1
    assert len(handled) == 1
    assert response.json()["duplicate"] is True


@pytest.mark.django_db(transaction=True)
def test_webhook_uses_payload_hash_when_external_event_id_is_missing():
    body = b'{"type":"heartbeat","value":true}'
    handled = []
    register_webhook_provider("test-hash", "provider-secret", handled.append)

    for _ in range(2):
        Client().post(
            "/webhooks/test-hash/",
            data=body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=signature("provider-secret", body),
        )

    assert WebhookEvent.objects.filter(provider="test-hash").count() == 1
    assert len(handled) == 1


@pytest.mark.django_db(transaction=True)
def test_webhook_acknowledges_after_handoff_without_running_handler_in_view():
    body = b'{"type":"invoice.created","id":"evt-async"}'
    handled = []
    register_webhook_provider("test-async", "provider-secret", handled.append)

    with patch("apps.platform_runtime.webhooks.process_webhook_event.enqueue") as enqueue:
        response = Client().post(
            "/webhooks/test-async/",
            data=body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=signature("provider-secret", body),
        )

    assert response.status_code == 202
    assert handled == []
    enqueue.assert_called_once()
