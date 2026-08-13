from django.dispatch import receiver
from django.tasks import TaskResultStatus
from django.tasks.signals import task_enqueued, task_finished, task_started

from .models import RuntimeLog
from .tasks import (
    PLATFORM_CORRELATION_ID_KWARG,
    PLATFORM_IDEMPOTENCY_KWARG,
    is_registered_platform_task,
    reset_current_task_result_id,
    set_current_task_result_id,
)


def _runtime_log_defaults(task_result) -> dict:
    return {
        "task_name": task_result.task.module_path,
        "backend": task_result.backend,
        "idempotency_key": task_result.kwargs.get(PLATFORM_IDEMPOTENCY_KWARG),
        "correlation_id": task_result.kwargs.get(PLATFORM_CORRELATION_ID_KWARG),
        "event_type": "task",
        "severity": "info",
    }


def _get_or_create_log(task_result) -> tuple[RuntimeLog, bool]:
    return RuntimeLog.objects.get_or_create(
        task_result_id=task_result.id,
        defaults={
            **_runtime_log_defaults(task_result),
            "status": RuntimeLog.Status.QUEUED,
        },
    )


@receiver(task_enqueued)
def record_task_enqueued(sender, task_result, **kwargs):
    if not is_registered_platform_task(task_result.task):
        return

    log, _ = _get_or_create_log(task_result)
    log.enqueued_at = task_result.enqueued_at
    log.idempotency_key = task_result.kwargs.get(PLATFORM_IDEMPOTENCY_KWARG)
    log.correlation_id = task_result.kwargs.get(PLATFORM_CORRELATION_ID_KWARG)
    log.status = RuntimeLog.Status.QUEUED
    log.save(
        update_fields=[
            "enqueued_at",
            "idempotency_key",
            "correlation_id",
            "status",
            "updated",
        ]
    )


@receiver(task_started)
def record_task_started(sender, task_result, **kwargs):
    if not is_registered_platform_task(task_result.task):
        return

    set_current_task_result_id(task_result.id)
    log, _ = _get_or_create_log(task_result)
    log.enqueued_at = task_result.enqueued_at
    log.idempotency_key = task_result.kwargs.get(PLATFORM_IDEMPOTENCY_KWARG)
    log.correlation_id = task_result.kwargs.get(PLATFORM_CORRELATION_ID_KWARG)
    log.started_at = task_result.started_at
    log.status = RuntimeLog.Status.STARTED
    log.save(
        update_fields=[
            "enqueued_at",
            "idempotency_key",
            "correlation_id",
            "started_at",
            "status",
            "updated",
        ]
    )


@receiver(task_finished)
def record_task_finished(sender, task_result, **kwargs):
    if not is_registered_platform_task(task_result.task):
        return

    log, _ = _get_or_create_log(task_result)
    log.enqueued_at = task_result.enqueued_at
    log.idempotency_key = task_result.kwargs.get(PLATFORM_IDEMPOTENCY_KWARG)
    log.correlation_id = task_result.kwargs.get(PLATFORM_CORRELATION_ID_KWARG)
    log.started_at = task_result.started_at
    log.finished_at = task_result.finished_at
    log.status = (
        RuntimeLog.Status.TIMEOUT
        if task_result.errors
        and task_result.errors[-1].exception_class_path.endswith("TaskTimeoutError")
        else RuntimeLog.Status.FAILED
        if task_result.status == TaskResultStatus.FAILED
        else RuntimeLog.Status.SUCCEEDED
    )
    log.severity = "error" if log.status != RuntimeLog.Status.SUCCEEDED else "info"
    if log.started_at and log.finished_at:
        log.duration_ms = max(
            0,
            int((log.finished_at - log.started_at).total_seconds() * 1000),
        )
    log.error_class = (
        task_result.errors[-1].exception_class_path if task_result.errors else ""
    )
    log.save(
        update_fields=[
            "enqueued_at",
            "idempotency_key",
            "correlation_id",
            "started_at",
            "finished_at",
            "duration_ms",
            "severity",
            "status",
            "error_class",
            "updated",
        ]
    )
    reset_current_task_result_id()
