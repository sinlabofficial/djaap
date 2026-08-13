from datetime import date, datetime, time, timedelta
from typing import Any

from auditlog.models import LogEntry
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Prefetch, Q, QuerySet
from django.utils import timezone

from apps.core.models import OrganizationSettings, Permission, Role, User, UserRole
from apps.platform_runtime.models import RuntimeLog, WebhookEvent

LOG_TABS: dict[str, dict[str, Any]] = {
    "access": {
        "label": "Access Logs",
        "models": (User, Role, Permission, UserRole, OrganizationSettings),
    },
    "background_jobs": {
        "label": "Background Jobs",
    },
    "webhooks": {
        "label": "Webhooks",
    },
    "realtime": {
        "label": "Realtime",
    },
}


def dashboard_summary_get() -> dict:
    """Return global identity and access metrics for the dashboard home."""
    users = User.objects.filter(deleted__isnull=True)
    return {
        "total_roles": Role.objects.filter(deleted__isnull=True).count(),
        "total_users": users.count(),
        "active_users": users.filter(is_active=True).count(),
        "recent_users": users.prefetch_related(
            Prefetch(
                "user_roles",
                queryset=UserRole.objects.filter(deleted__isnull=True).select_related(
                    "role"
                ),
            )
        )[:5],
    }


def dashboard_runtime_summary_get() -> dict:
    """Return redacted Platform Runtime health metrics for the dashboard."""
    retention_cutoff = timezone.now() - timedelta(
        days=settings.PLATFORM_RUNTIME_RETENTION_DAYS
    )
    task_logs = RuntimeLog.objects.filter(
        ~Q(event_type__startswith="webhook."),
        ~Q(event_type__startswith="realtime."),
        created__gte=retention_cutoff,
    )
    failed_task_statuses = [RuntimeLog.Status.FAILED, RuntimeLog.Status.TIMEOUT]
    failed_tasks = task_logs.filter(status__in=failed_task_statuses).order_by(
        "-created"
    )
    total_tasks = task_logs.count()
    retried_tasks = task_logs.filter(attempt__gt=1).count()
    average_duration = task_logs.filter(duration_ms__isnull=False).aggregate(
        value=Avg("duration_ms")
    )["value"]
    queued_task = task_logs.filter(status=RuntimeLog.Status.QUEUED).order_by(
        "enqueued_at", "created"
    ).first()
    webhook_records = WebhookEvent.objects.filter(received_at__gte=retention_cutoff)
    webhook_attention = webhook_records.filter(
        status__in=[WebhookEvent.Status.FAILED, WebhookEvent.Status.REJECTED]
    ).order_by("-received_at")
    failed_webhooks = webhook_records.filter(status=WebhookEvent.Status.FAILED)

    return {
        "failed_task_count": failed_tasks.count(),
        "failed_tasks": failed_tasks[:5],
        "failed_webhook_count": failed_webhooks.count(),
        "webhook_attention_count": webhook_attention.count(),
        "webhooks_needing_attention": webhook_attention[:5],
        "retry_rate": round((retried_tasks / total_tasks) * 100, 1)
        if total_tasks
        else 0.0,
        "oldest_queued_task": queued_task,
        "average_duration_ms": round(average_duration) if average_duration else 0,
        "timeout_count": task_logs.filter(status=RuntimeLog.Status.TIMEOUT).count(),
        "webhook_rejection_count": webhook_records.filter(
            status=WebhookEvent.Status.REJECTED
        ).count(),
    }


def dashboard_users_list(
    *, email: str = "", is_staff: str = "", is_active: str = "", role_id: str = ""
) -> QuerySet[User]:
    """Return filtered, active users for dashboard administration views."""
    queryset = (
        User.objects.filter(deleted__isnull=True)
        .prefetch_related(
            Prefetch(
                "user_roles",
                queryset=UserRole.objects.filter(deleted__isnull=True).select_related(
                    "role"
                ),
            )
        )
        .order_by("-created")
    )

    if email:
        queryset = queryset.filter(email__icontains=email)
    if is_staff in {"true", "false"}:
        queryset = queryset.filter(is_staff=is_staff == "true")
    if is_active in {"true", "false"}:
        queryset = queryset.filter(is_active=is_active == "true")
    if role_id:
        queryset = queryset.filter(user_roles__role_id=role_id).distinct()
    return queryset


def dashboard_roles_list() -> QuerySet[Role]:
    """Return active roles ordered for dashboard administration views."""
    return Role.objects.filter(deleted__isnull=True).order_by("-level")


def dashboard_permissions_list() -> QuerySet[Permission]:
    """Return active permissions for global RBAC administration."""
    return Permission.objects.filter(deleted__isnull=True).order_by(
        "resource", "action"
    )


def dashboard_role_detail_get(*, role_id):
    """Return an active role and its global user count."""
    role = (
        Role.objects.filter(deleted__isnull=True, id=role_id)
        .prefetch_related("permissions")
        .first()
    )
    if role is None:
        return None
    user_count = UserRole.objects.filter(role=role, deleted__isnull=True).count()
    return role, user_count


def dashboard_log_entries(
    *,
    tab: str,
    status: str = "",
    action: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[LogEntry]:
    """Return display-ready audit entries for one administrator log tab."""
    tab_config = LOG_TABS.get(tab, LOG_TABS["access"])
    content_types = ContentType.objects.get_for_models(*tab_config["models"])
    queryset: QuerySet[LogEntry] = (
        LogEntry.objects.filter(content_type__in=content_types.values())
        .select_related("actor", "content_type")
        .order_by("-timestamp")
    )

    if action:
        queryset = queryset.filter(action=action)
    if date_from:
        start = timezone.make_aware(datetime.combine(date_from, time.min))
        queryset = queryset.filter(timestamp__gte=start)
    if date_to:
        end = timezone.make_aware(
            datetime.combine(date_to + timedelta(days=1), time.min)
        )
        queryset = queryset.filter(timestamp__lt=end)

    entries = list(queryset)
    for entry in entries:
        metadata = (
            entry.additional_data if isinstance(entry.additional_data, dict) else {}
        )
        entry.log_status = str(metadata.get("status", "success")).lower()
        entry.action_label = entry.get_action_display()
        entry.model_label = entry.content_type.model.replace("_", " ").title()

    if status:
        entries = [entry for entry in entries if entry.log_status == status]
    return entries


def dashboard_runtime_log_entries(
    *,
    status: str = "",
    event_type: str = "",
    severity: str = "",
    correlation_id: str = "",
    category: str = "",
    provider: str = "",
    external_event_id: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[RuntimeLog]:
    """Return paginatable, filtered task Runtime Logs for the Dashboard."""
    queryset = RuntimeLog.objects.order_by("-created")

    if status:
        queryset = queryset.filter(status=status)
    if event_type:
        queryset = queryset.filter(event_type=event_type)
    if category:
        queryset = queryset.filter(event_type__startswith=f"{category}.")
    if correlation_id:
        queryset = queryset.filter(correlation_id__icontains=correlation_id)
    if severity:
        queryset = queryset.filter(severity=severity)
    if provider:
        queryset = queryset.filter(safe_metadata__provider=provider)
    if external_event_id:
        queryset = queryset.filter(safe_metadata__external_event_id=external_event_id)
    if date_from:
        start = timezone.make_aware(datetime.combine(date_from, time.min))
        queryset = queryset.filter(created__gte=start)
    if date_to:
        end = timezone.make_aware(
            datetime.combine(date_to + timedelta(days=1), time.min)
        )
        queryset = queryset.filter(created__lt=end)

    return queryset


def dashboard_webhook_log_entries(
    *,
    status: str = "",
    provider: str = "",
    external_event_id: str = "",
    correlation_id: str = "",
    severity: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[RuntimeLog]:
    """Return safe webhook lifecycle logs for the dashboard."""
    return dashboard_runtime_log_entries(
        status=RuntimeLog.Status.FAILED if status == "failed" else "",
        event_type=f"webhook.{status}" if status else "",
        severity=severity,
        correlation_id=correlation_id,
        category="webhook",
        provider=provider,
        external_event_id=external_event_id,
        date_from=date_from,
        date_to=date_to,
    )


def dashboard_realtime_log_entries(
    *,
    category: str = "",
    status: str = "",
    event_type: str = "",
    severity: str = "",
    provider: str = "",
    external_event_id: str = "",
    correlation_id: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[RuntimeLog]:
    """Return paginatable, safe Realtime Runtime Logs."""
    return dashboard_runtime_log_entries(
        category=category or "realtime",
        status=status,
        event_type=event_type,
        severity=severity,
        provider=provider,
        external_event_id=external_event_id,
        correlation_id=correlation_id,
        date_from=date_from,
        date_to=date_to,
    )
