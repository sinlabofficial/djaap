import time

import pytest
from django.db import transaction
from django.tasks import TaskResultStatus

from apps.platform_runtime.models import RuntimeLog
from apps.platform_runtime.tasks import (
    enqueue_after_commit,
    platform_task,
)


@platform_task
def add_numbers(left: int, right: int) -> int:
    return left + right


@platform_task
def fail_task() -> None:
    raise ValueError("safe failure")


class TransientFailureError(Exception):
    pass


retry_attempts = 0
permanent_attempts = 0
side_effect_calls = 0


@platform_task(retry_for=(TransientFailureError,), max_attempts=3)
def eventually_succeeds() -> str:
    global retry_attempts
    retry_attempts += 1
    if retry_attempts < 3:
        raise TransientFailureError("try again")
    return "done"


@platform_task(retry_for=(TransientFailureError,), max_attempts=3)
def permanently_fails() -> None:
    global permanent_attempts
    permanent_attempts += 1
    raise ValueError("permanent failure")


@platform_task
def record_side_effect() -> None:
    global side_effect_calls
    side_effect_calls += 1


@platform_task(timeout_seconds=0.01)
def slow_task() -> None:
    time.sleep(0.05)


@pytest.mark.django_db
def test_platform_task_executes_with_immediate_backend_and_logs_lifecycle():
    result = add_numbers.enqueue(2, 3, correlation_id="corr-1")

    assert result.status == TaskResultStatus.SUCCESSFUL
    assert result.return_value == 5

    log = RuntimeLog.objects.get(task_result_id=result.id)
    assert log.task_name == add_numbers.module_path
    assert log.status == RuntimeLog.Status.SUCCEEDED
    assert log.backend == "default"
    assert log.correlation_id == "corr-1"
    assert log.enqueued_at is not None
    assert log.started_at is not None
    assert log.finished_at is not None
    assert log.duration_ms is not None
    assert log.error_class == ""


@pytest.mark.django_db
def test_platform_task_failure_is_recorded_without_task_arguments():
    result = fail_task.enqueue()

    assert result.status == TaskResultStatus.FAILED

    log = RuntimeLog.objects.get(task_result_id=result.id)
    assert log.status == RuntimeLog.Status.FAILED
    assert log.error_class == "builtins.ValueError"
    assert log.safe_metadata == {}


@pytest.mark.django_db
def test_platform_task_idempotency_key_prevents_duplicate_side_effect():
    global side_effect_calls
    side_effect_calls = 0

    first = record_side_effect.enqueue(idempotency_key="event-1")
    second = record_side_effect.enqueue(idempotency_key="event-1")

    assert first.status == TaskResultStatus.SUCCESSFUL
    assert second.status == TaskResultStatus.SUCCESSFUL
    assert side_effect_calls == 1
    assert RuntimeLog.objects.filter(idempotency_key="event-1").count() == 2


@pytest.mark.django_db
def test_platform_task_retries_transient_failure_with_bounded_attempts():
    global retry_attempts
    retry_attempts = 0

    result = eventually_succeeds.enqueue()

    assert result.status == TaskResultStatus.SUCCESSFUL
    assert retry_attempts == 3
    log = RuntimeLog.objects.get(task_result_id=result.id)
    assert log.status == RuntimeLog.Status.SUCCEEDED
    assert log.attempt == 3


@pytest.mark.django_db
def test_platform_task_does_not_retry_non_transient_failure():
    global permanent_attempts
    permanent_attempts = 0

    result = permanently_fails.enqueue()

    assert result.status == TaskResultStatus.FAILED
    assert permanent_attempts == 1


@pytest.mark.django_db
def test_platform_task_timeout_is_a_failed_runtime_result():
    result = slow_task.enqueue()

    assert result.status == TaskResultStatus.FAILED
    assert result.errors[-1].exception_class_path.endswith("TaskTimeoutError")
    log = RuntimeLog.objects.get(task_result_id=result.id)
    assert log.status == RuntimeLog.Status.TIMEOUT
    assert log.error_class.endswith("TaskTimeoutError")


@pytest.mark.django_db(transaction=True)
def test_enqueue_after_commit_waits_for_commit_and_notifies_after_rollback():
    global side_effect_calls
    side_effect_calls = 0

    with transaction.atomic():
        enqueue_after_commit(record_side_effect, idempotency_key="committed")
        assert side_effect_calls == 0

    assert side_effect_calls == 1

    with pytest.raises(RuntimeError), transaction.atomic():
        enqueue_after_commit(record_side_effect, idempotency_key="rolled-back")
        raise RuntimeError("rollback")

    assert side_effect_calls == 1
    assert not RuntimeLog.objects.filter(idempotency_key="rolled-back").exists()
