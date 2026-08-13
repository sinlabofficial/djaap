import importlib.util

import pytest
from django.conf import settings
from django.urls import NoReverseMatch, reverse


def test_workspace_and_agent_apps_are_not_installed():
    assert "apps.workspaces" not in settings.INSTALLED_APPS
    assert "apps.agents" not in settings.INSTALLED_APPS


def test_removed_runtime_modules_are_not_importable():
    assert importlib.util.find_spec("apps.workspaces") is None
    assert importlib.util.find_spec("apps.agents") is None


@pytest.mark.django_db
def test_removed_runtime_routes_are_not_registered(client):
    with pytest.raises(NoReverseMatch):
        reverse("dashboard:workspace_list")

    response = client.get("/dashboard/workspaces/")

    assert response.status_code == 404


def test_agent_queue_settings_are_not_configured():
    assert not hasattr(settings, "AGENT_MODEL")
    assert not hasattr(settings, "CELERY_BROKER_URL")
    assert not hasattr(settings, "CELERY_RESULT_BACKEND")
    assert not hasattr(settings, "CELERY_BEAT_SCHEDULE")
