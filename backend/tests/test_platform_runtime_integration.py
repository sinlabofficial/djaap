import importlib

import pytest
from django.conf import settings
from django.urls import reverse

from apps.core.models import Permission, Role, User, UserRole
from apps.platform_runtime.models import RealtimeEvent
from apps.platform_runtime.realtime import publish_realtime_event


def test_public_runtime_surface_imports_without_optional_adapters():
    tasks = importlib.import_module("apps.platform_runtime.tasks")
    realtime = importlib.import_module("apps.platform_runtime.realtime")
    webhooks = importlib.import_module("apps.platform_runtime.webhooks")
    maintenance = importlib.import_module("apps.platform_runtime.maintenance")

    assert callable(tasks.platform_task)
    assert callable(tasks.enqueue_after_commit)
    assert callable(realtime.publish_realtime_event)
    assert callable(webhooks.register_webhook_provider)
    assert callable(webhooks.receive_webhook)
    assert callable(maintenance.cleanup_expired_runtime_data)
    assert settings.TASKS["default"]["BACKEND"].endswith("ImmediateBackend")
    assert settings.REALTIME_ENABLED is False


@pytest.mark.parametrize(
    "module_name", [
        "apps.platform_runtime.tasks",
        "apps.platform_runtime.realtime",
        "apps.platform_runtime.webhooks",
        "apps.platform_runtime.maintenance",
    ]
)
def test_platform_runtime_public_modules_are_importable(module_name):
    assert importlib.import_module(module_name)


@pytest.mark.django_db
def test_permission_filtered_http_fallback_is_authoritative(client):
    viewer = User.objects.create_user(email="viewer@example.com")
    event = publish_realtime_event(
        event_type="order.updated",
        required_permission="orders:view",
        payload={"id": "order-1", "token": "must-not-leak"},
    )
    client.force_login(viewer)

    denied = client.get(reverse("realtime-events"), {"since": "2000-01-01T00:00:00+00:00"})
    assert denied.status_code == 200
    assert denied.json()["events"] == []

    permission = Permission.objects.create(resource="orders", action="view")
    role = Role.objects.create(name="Order viewer", level=10)
    role.permissions.add(permission)
    UserRole.objects.create(user=viewer, role=role)

    allowed = client.get(
        reverse("realtime-events"), {"since": "2000-01-01T00:00:00+00:00"}
    )
    assert allowed.status_code == 200
    assert allowed.json()["events"][0]["event_id"] == str(event.id)
    assert "must-not-leak" not in allowed.content.decode()
    assert RealtimeEvent.objects.filter(id=event.id).exists()
