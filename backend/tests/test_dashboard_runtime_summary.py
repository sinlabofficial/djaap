from datetime import timedelta

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Permission, Role, User, UserRole
from apps.dashboard.selectors import dashboard_runtime_summary_get
from apps.platform_runtime.models import RuntimeLog, WebhookEvent


def grant_runtime_log_view(user):
    permission = Permission.objects.create(
        resource="runtime_logs",
        action="view",
        description="View runtime logs",
    )
    role = Role.objects.create(name="Runtime observer", level=10)
    role.permissions.add(permission)
    UserRole.objects.create(user=user, role=role)


def make_task_log(*, result_id, status, attempt=1, duration_ms=None, created=None):
    log = RuntimeLog.objects.create(
        task_result_id=result_id,
        task_name="apps.example.tasks.sync_item",
        backend="default",
        status=status,
        event_type="task",
        severity="error" if status != RuntimeLog.Status.SUCCEEDED else "info",
        attempt=attempt,
        duration_ms=duration_ms,
        safe_metadata={"secret": "must-not-render"},
    )
    if created is not None:
        RuntimeLog.objects.filter(id=log.id).update(created=created)
        log.created = created
    return log


def make_webhook(*, event_id, status):
    return WebhookEvent.objects.create(
        provider="billing",
        event_type="invoice.updated",
        external_event_id=event_id,
        dedupe_key=f"dedupe-{event_id}",
        payload_hash="a" * 64,
        payload_reference=f"ref-{event_id}",
        safe_payload={"secret": "must-not-render"},
        safe_metadata={"provider": "billing"},
        status=status,
    )


@pytest.mark.django_db
def test_runtime_summary_selector_returns_actionable_metrics_without_payloads():
    now = timezone.now()
    make_task_log(
        result_id="queued-old",
        status=RuntimeLog.Status.QUEUED,
        created=now - timedelta(hours=3),
    )
    make_task_log(
        result_id="failed-task",
        status=RuntimeLog.Status.FAILED,
        attempt=2,
        duration_ms=100,
    )
    make_task_log(
        result_id="timeout-task",
        status=RuntimeLog.Status.TIMEOUT,
        duration_ms=300,
    )
    make_task_log(
        result_id="successful-task",
        status=RuntimeLog.Status.SUCCEEDED,
        duration_ms=200,
    )
    make_webhook(event_id="failed-webhook", status=WebhookEvent.Status.FAILED)
    make_webhook(event_id="rejected-webhook", status=WebhookEvent.Status.REJECTED)

    summary = dashboard_runtime_summary_get()

    assert summary["failed_task_count"] == 2
    assert [log.task_result_id for log in summary["failed_tasks"]] == [
        "timeout-task",
        "failed-task",
    ]
    assert summary["failed_webhook_count"] == 1
    assert summary["webhook_attention_count"] == 2
    assert summary["retry_rate"] == 25.0
    assert summary["oldest_queued_task"].task_result_id == "queued-old"
    assert summary["average_duration_ms"] == 200
    assert summary["timeout_count"] == 1
    assert summary["webhook_rejection_count"] == 1
    assert "must-not-render" not in str(summary)


@pytest.mark.django_db
def test_dashboard_home_shows_runtime_summary_only_with_permission(client):
    user = User.objects.create_user(email="member@example.com", password="testpass123")
    client.force_login(user)

    hidden_response = client.get(reverse("dashboard:home"))

    assert hidden_response.status_code == 200
    assert b"Platform Runtime health" not in hidden_response.content

    grant_runtime_log_view(user)
    make_task_log(result_id="visible-failure", status=RuntimeLog.Status.FAILED)
    make_webhook(event_id="visible-rejection", status=WebhookEvent.Status.REJECTED)

    visible_response = client.get(reverse("dashboard:home"))

    assert visible_response.status_code == 200
    assert b"Platform Runtime health" in visible_response.content
    assert b">Failed tasks<" in visible_response.content
    assert b">Failed webhooks<" in visible_response.content
    assert b"visible-failure" in visible_response.content
    assert b"visible-rejection" in visible_response.content
    assert b"must-not-render" not in visible_response.content


@pytest.mark.django_db
@override_settings(PLATFORM_RUNTIME_RETENTION_DAYS=30)
def test_runtime_summary_excludes_records_outside_retention_window():
    old_time = timezone.now() - timedelta(days=31)
    old_task = make_task_log(
        result_id="expired-failure", status=RuntimeLog.Status.FAILED
    )
    RuntimeLog.objects.filter(id=old_task.id).update(created=old_time)
    old_webhook = make_webhook(
        event_id="expired-rejection", status=WebhookEvent.Status.REJECTED
    )
    WebhookEvent.objects.filter(id=old_webhook.id).update(received_at=old_time)

    summary = dashboard_runtime_summary_get()

    assert summary["failed_task_count"] == 0
    assert summary["failed_webhook_count"] == 0
    assert summary["webhook_attention_count"] == 0
    assert summary["webhook_rejection_count"] == 0
    assert list(summary["failed_tasks"]) == []
    assert list(summary["webhooks_needing_attention"]) == []
