from datetime import date, timedelta

import pytest
from auditlog.models import LogEntry

from apps.dashboard.selectors import dashboard_log_entries


@pytest.mark.django_db
def test_dashboard_log_selector_supports_access_filters():
    entries = dashboard_log_entries(
        tab="removed-tab",
        action=LogEntry.Action.CREATE,
        date_from=date.today() - timedelta(days=1),
        date_to=date.today(),
    )

    assert entries == []
