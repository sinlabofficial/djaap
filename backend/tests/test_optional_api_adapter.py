import pytest
from django.conf import settings
from django.urls import NoReverseMatch, reverse


def test_api_is_an_optional_adapter_and_never_owns_dashboard_routes():
    assert ("apps.api" in settings.INSTALLED_APPS) is settings.API_ENABLED
    assert reverse("dashboard:home") == "/dashboard/"
    if settings.API_ENABLED:
        assert reverse("api:health_check") == "/api/health/"
    else:
        with pytest.raises(NoReverseMatch):
            reverse("api:health_check")


@pytest.mark.django_db
def test_api_has_no_out_of_scope_runtime_routes(client):
    for route_name in ("api:workspace-list", "api:dataset-list", "api:agent-run-list"):
        with pytest.raises(NoReverseMatch):
            reverse(route_name)

    assert client.get("/dashboard/").status_code == 302
