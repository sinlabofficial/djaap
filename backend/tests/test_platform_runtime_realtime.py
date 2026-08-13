import re
from unittest.mock import patch

import pytest
from django.db import transaction
from django.urls import reverse

from apps.core.models import Permission, Role, User, UserRole
from apps.platform_runtime.models import RealtimeEvent
from apps.platform_runtime.realtime import publish_realtime_event


@pytest.mark.django_db(transaction=True)
def test_realtime_event_dispatches_only_after_commit_and_redacts_payload():
    with patch("apps.platform_runtime.realtime._dispatch_realtime_event") as dispatch:
        with transaction.atomic():
            event = publish_realtime_event(
                event_type="order.updated",
                required_permission="orders:view",
                correlation_id="corr-1",
                payload={"id": "order-1", "access_token": "secret", "label": "Ready"},
            )
            dispatch.assert_not_called()
        dispatch.assert_called_once_with(event.id)

    event.refresh_from_db()
    assert event.safe_payload == {
        "id": "order-1",
        "access_token": "[REDACTED]",
        "label": "Ready",
    }


@pytest.mark.django_db(transaction=True)
def test_realtime_event_is_not_published_when_transaction_rolls_back():
    with (
        patch("apps.platform_runtime.realtime._dispatch_realtime_event") as dispatch,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        publish_realtime_event(event_type="order.updated", payload={"id": "1"})
        raise RuntimeError("rollback")

    dispatch.assert_not_called()
    assert not RealtimeEvent.objects.filter(event_type="order.updated").exists()


@pytest.mark.django_db(transaction=True)
def test_http_fallback_is_session_authenticated_and_permission_filtered(client):
    viewer = User.objects.create_user(email="viewer@example.com", password="testpass123")
    event = publish_realtime_event(
        event_type="order.updated",
        required_permission="orders:view",
        payload={"id": "order-1"},
    )
    client.force_login(viewer)

    response = client.get(reverse("realtime-events"))
    assert response.status_code == 200
    assert response.json()["events"] == []

    permission = Permission.objects.create(resource="orders", action="view")
    role = Role.objects.create(name="Order viewer", level=10)
    role.permissions.add(permission)
    UserRole.objects.create(user=viewer, role=role)

    response = client.get(reverse("realtime-events"), {"since": "2000-01-01T00:00:00+00:00"})
    assert response.status_code == 200
    assert response.json()["events"][0]["event_id"] == str(event.id)


@pytest.mark.django_db
def test_http_fallback_requires_session(client):
    response = client.get(reverse("realtime-events"))
    assert response.status_code == 302
    assert "/dashboard/login/" in response.url


def test_realtime_group_names_are_valid_and_bounded():
    from apps.platform_runtime.realtime import _group_name

    assert _group_name("") == "realtime-broadcast"
    assert re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", _group_name("orders:view"))



def test_asgi_boots_without_channels_dependency():
    import config.asgi

    assert config.asgi.application is not None
