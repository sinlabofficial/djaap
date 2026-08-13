import pytest
from django.urls import reverse

from apps.core.models import Permission, Role, User, UserRole
from apps.platform_runtime.models import RuntimeLog


def make_runtime_log(**overrides):
    values = {
        "task_result_id": overrides.pop("task_result_id", "result-1"),
        "task_name": "apps.example.tasks.sync_item",
        "backend": "default",
        "status": RuntimeLog.Status.SUCCEEDED,
        "event_type": "task.completed",
        "severity": "info",
        "correlation_id": "corr-1",
        "safe_metadata": {"secret": "do-not-display"},
    }
    values.update(overrides)
    return RuntimeLog.objects.create(**values)


def grant_runtime_log_view(user):
    permission = Permission.objects.create(
        resource="runtime_logs",
        action="view",
        description="View runtime logs",
    )
    role = Role.objects.create(name="Runtime observer", level=10)
    role.permissions.add(permission)
    UserRole.objects.create(user=user, role=role)


@pytest.mark.django_db
def test_staff_can_filter_background_job_logs_without_sensitive_metadata(client):
    staff = User.objects.create_user(
        email="operator@example.com",
        password="testpass123",
        is_staff=True,
    )
    grant_runtime_log_view(staff)
    make_runtime_log(
        status=RuntimeLog.Status.FAILED,
        severity="error",
        event_type="task.failed",
        correlation_id="corr-failed",
        task_result_id="failed-result",
    )
    make_runtime_log(
        status=RuntimeLog.Status.SUCCEEDED,
        correlation_id="corr-success",
        task_result_id="success-result",
    )
    client.force_login(staff)

    response = client.get(
        reverse("dashboard:logs"),
        {
            "tab": "background_jobs",
            "status": RuntimeLog.Status.FAILED,
            "event_type": "task.failed",
            "severity": "error",
            "correlation_id": "corr-failed",
        },
    )

    assert response.status_code == 200
    assert b"Background Jobs" in response.content
    assert b"failed-result" in response.content
    assert b"success-result" not in response.content
    assert b"do-not-display" not in response.content
    assert response.context["runtime_page_obj"].paginator.count == 1


@pytest.mark.django_db
def test_background_job_logs_are_paginated(client):
    staff = User.objects.create_user(
        email="operator@example.com",
        password="testpass123",
        is_staff=True,
    )
    grant_runtime_log_view(staff)
    for index in range(21):
        make_runtime_log(task_result_id=f"result-{index}")
    client.force_login(staff)

    response = client.get(
        reverse("dashboard:logs"),
        {"tab": "background_jobs", "page": 2},
    )

    assert response.status_code == 200
    page = response.context["runtime_page_obj"]
    assert page.paginator.count == 21
    assert len(page.object_list) == 1


@pytest.mark.django_db
def test_background_job_logs_follow_runtime_log_permission(client):
    user = User.objects.create_user(
        email="operator@example.com",
        password="testpass123",
    )
    client.force_login(user)
    url = reverse("dashboard:logs") + "?tab=background_jobs"

    assert client.get(url).status_code == 302

    permission = Permission.objects.create(
        resource="runtime_logs",
        action="view",
        description="View runtime logs",
    )
    role = Role.objects.create(name="Runtime observer", level=10)
    role.permissions.add(permission)
    UserRole.objects.create(user=user, role=role)

    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_realtime_logs_are_filtered_paginated_redacted_and_refreshable(client):
    staff = User.objects.create_user(
        email="realtime-operator@example.com",
        password="testpass123",
        is_staff=True,
    )
    grant_runtime_log_view(staff)
    for index in range(21):
        make_runtime_log(
            task_result_id=f"realtime-{index}",
            task_name="platform_runtime.realtime",
            event_type="realtime.publish_failed",
            status=RuntimeLog.Status.FAILED,
            severity="error",
            correlation_id="realtime-correlation",
            safe_metadata={"secret": "must-not-render", "provider": "internal"},
        )
    make_runtime_log(
        task_result_id="webhook-not-realtime",
        event_type="webhook.failed",
        status=RuntimeLog.Status.FAILED,
        severity="error",
    )
    client.force_login(staff)

    response = client.get(
        reverse("dashboard:logs"),
        {
            "tab": "realtime",
            "category": "realtime",
            "event_type": "realtime.publish_failed",
            "status": RuntimeLog.Status.FAILED,
            "severity": "error",
            "page": 2,
        },
    )

    assert response.status_code == 200
    assert response.context["realtime_page_obj"].paginator.count == 21
    assert len(response.context["realtime_page_obj"].object_list) == 1
    assert b"realtime-20" not in response.content
    assert b"webhook-not-realtime" not in response.content
    assert b"must-not-render" not in response.content
    assert b"realtime-log-region" in response.content
    assert b'hx-get="/dashboard/logs/"' in response.content
    assert b'hx-include="#realtime-log-filter-form"' in response.content
