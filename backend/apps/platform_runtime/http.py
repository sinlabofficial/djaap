from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.core.selectors import user_has_permission

from .realtime import _envelope, realtime_events_since


@login_required(login_url="/dashboard/login/")
@require_GET
def realtime_events(request):
    since = None
    value = request.GET.get("since")
    if value:
        try:
            since = datetime.fromisoformat(value)
        except ValueError:
            return JsonResponse({"detail": "invalid since timestamp"}, status=400)
    events = []
    for event in realtime_events_since(since=since):
        permission = event.required_permission
        user = request.user
        if permission and not (
            user.is_superuser or user_has_permission(user=user, permission=permission)
        ):
            continue
        events.append(_envelope(event))
        if len(events) >= 100:
            break
    return JsonResponse({"events": events})
