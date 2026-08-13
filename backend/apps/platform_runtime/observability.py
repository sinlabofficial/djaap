import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import RealtimeEvent, RuntimeLog, WebhookEvent
from .redaction import redact_value

logger = logging.getLogger("apps.platform_runtime")


def _runtime_event_payload(instance: RuntimeLog) -> dict:
    return {
        "event_type": instance.event_type,
        "status": instance.status,
        "severity": instance.severity,
        "task_name": instance.task_name,
        "backend": instance.backend,
        "correlation_id": instance.correlation_id,
        "attempt": instance.attempt,
        "duration_ms": instance.duration_ms,
        "error_class": instance.error_class or None,
        "safe_metadata": redact_value(instance.safe_metadata),
    }


@receiver(pre_save, sender=RuntimeLog)
def redact_runtime_log(sender, instance: RuntimeLog, **kwargs):
    instance.safe_metadata = redact_value(instance.safe_metadata)


@receiver(pre_save, sender=WebhookEvent)
def redact_webhook_event(sender, instance: WebhookEvent, **kwargs):
    instance.safe_payload = redact_value(instance.safe_payload)
    instance.safe_metadata = redact_value(instance.safe_metadata)


@receiver(pre_save, sender=RealtimeEvent)
def redact_realtime_event(sender, instance: RealtimeEvent, **kwargs):
    instance.safe_payload = redact_value(instance.safe_payload)


@receiver(post_save, sender=RuntimeLog)
def emit_runtime_log(sender, instance: RuntimeLog, **kwargs):
    logger.info(
        "platform_runtime_event",
        extra={"platform_runtime_event": _runtime_event_payload(instance)},
    )
