from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class RuntimeLog(BaseModel):
    """Safe lifecycle record for a task owned by Platform Runtime."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        STARTED = "started", "Started"
        RETRYING = "retrying", "Retrying"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        TIMEOUT = "timeout", "Timeout"

    task_result_id = models.CharField(max_length=64, unique=True)
    task_name = models.CharField(max_length=255)
    backend = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status, db_index=True)
    event_type = models.CharField(max_length=100, default="task")
    severity = models.CharField(max_length=20, default="info", db_index=True)
    correlation_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    attempt = models.PositiveIntegerField(default=1)
    idempotency_key = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    enqueued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error_class = models.CharField(max_length=255, blank=True)
    safe_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["status", "-created"]),
            models.Index(fields=["task_name", "-created"]),
        ]

    def __str__(self) -> str:
        return f"{self.task_name} ({self.status})"


class TaskIdempotency(BaseModel):
    """Tracks a side-effecting Platform Runtime task key."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    task_name = models.CharField(max_length=255)
    key = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status)
    task_result_id = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task_name", "key"],
                name="platform_task_idempotency_unique",
            )
        ]


class WebhookEvent(BaseModel):
    """Verified inbound event metadata; raw webhook bodies are never stored."""

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        VERIFIED = "verified", "Verified"
        ENQUEUED = "enqueued", "Enqueued"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        REJECTED = "rejected", "Rejected"
        REPLAYED = "replayed", "Replayed"

    provider = models.CharField(max_length=100)
    replay_of = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replay"
    )
    event_type = models.CharField(max_length=150)
    external_event_id = models.CharField(max_length=255, blank=True, null=True)
    dedupe_key = models.CharField(max_length=255, unique=True)
    payload_hash = models.CharField(max_length=64)
    payload_reference = models.CharField(max_length=80)
    safe_payload = models.JSONField(default=dict, blank=True)
    correlation_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status, default=Status.RECEIVED, db_index=True)
    task_result_id = models.CharField(max_length=64, blank=True)
    safe_metadata = models.JSONField(default=dict, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["provider", "external_event_id"]),
            models.Index(fields=["status", "-received_at"]),
        ]


class RealtimeEvent(BaseModel):
    """Safe, short-lived notification envelope for optional realtime adapters."""

    event_type = models.CharField(max_length=150)
    required_permission = models.CharField(max_length=100, blank=True)
    correlation_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    safe_payload = models.JSONField(default=dict, blank=True)
    published_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["event_type", "-published_at"]),
            models.Index(fields=["expires_at", "-published_at"]),
        ]
