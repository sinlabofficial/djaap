import signal
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, overload

from django.db import IntegrityError, transaction
from django.tasks import Task
from django.tasks import task as django_task

from .models import RuntimeLog, TaskIdempotency

PLATFORM_RESULT_ID_KWARG = "_platform_task_result_id"
PLATFORM_IDEMPOTENCY_KWARG = "_platform_idempotency_key"
PLATFORM_CORRELATION_ID_KWARG = "_platform_correlation_id"

_registered_task_paths: set[str] = set()
_current_task_result_id: ContextVar[str | None] = ContextVar(
    "platform_runtime_task_result_id", default=None
)


class TaskTimeoutError(TimeoutError):
    """Raised when a Platform Runtime task exceeds its execution limit."""


@dataclass(frozen=True)
class TaskPolicy:
    retry_for: tuple[type[Exception], ...] = ()
    max_attempts: int = 1
    retry_backoff_seconds: float = 0
    timeout_seconds: float | None = None


class PlatformTask:
    """Backend-neutral facade around Django's Task contract."""

    def __init__(self, task: Task, policy: TaskPolicy):
        self._task = task
        self.policy = policy

    @property
    def name(self) -> str:
        return self._task.name

    @property
    def module_path(self) -> str:
        return self._task.module_path

    @property
    def backend(self) -> str:
        return self._task.backend

    def enqueue(
        self,
        *args: Any,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        **kwargs: Any,
    ):
        if idempotency_key is not None and not idempotency_key:
            raise ValueError("idempotency_key cannot be empty")
        if idempotency_key is not None:
            kwargs[PLATFORM_IDEMPOTENCY_KWARG] = idempotency_key
        if correlation_id is not None:
            kwargs[PLATFORM_CORRELATION_ID_KWARG] = correlation_id
        return self._task.enqueue(*args, **kwargs)

    async def aenqueue(
        self,
        *args: Any,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        **kwargs: Any,
    ):
        if idempotency_key is not None and not idempotency_key:
            raise ValueError("idempotency_key cannot be empty")
        if idempotency_key is not None:
            kwargs[PLATFORM_IDEMPOTENCY_KWARG] = idempotency_key
        if correlation_id is not None:
            kwargs[PLATFORM_CORRELATION_ID_KWARG] = correlation_id
        return await self._task.aenqueue(*args, **kwargs)

    def using(
        self,
        *,
        priority: int | None = None,
        queue_name: str | None = None,
        run_after: datetime | None = None,
        backend: str | None = None,
    ) -> PlatformTask:
        return PlatformTask(
            self._task.using(
                priority=priority,
                queue_name=queue_name,
                run_after=run_after,
                backend=backend,
            ),
            self.policy,
        )

    def get_result(self, result_id: str):
        return self._task.get_result(result_id)


@overload
def platform_task(
    function: Callable[..., Any],
    *,
    priority: int = 0,
    queue_name: str = "default",
    backend: str = "default",
    takes_context: bool = False,
    retry_for: tuple[type[Exception], ...] = (),
    max_attempts: int = 1,
    retry_backoff_seconds: float = 0,
    timeout_seconds: float | None = None,
) -> PlatformTask: ...


@overload
def platform_task(
    function: None = None,
    *,
    priority: int = 0,
    queue_name: str = "default",
    backend: str = "default",
    takes_context: bool = False,
    retry_for: tuple[type[Exception], ...] = (),
    max_attempts: int = 1,
    retry_backoff_seconds: float = 0,
    timeout_seconds: float | None = None,
) -> Callable[[Callable[..., Any]], PlatformTask]: ...


def platform_task(
    function: Callable[..., Any] | None = None,
    *,
    priority: int = 0,
    queue_name: str = "default",
    backend: str = "default",
    takes_context: bool = False,
    retry_for: tuple[type[Exception], ...] = (),
    max_attempts: int = 1,
    retry_backoff_seconds: float = 0,
    timeout_seconds: float | None = None,
) -> PlatformTask | Callable[[Callable[..., Any]], PlatformTask]:
    """Define a task with explicit, bounded reliability policy."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if retry_backoff_seconds < 0:
        raise ValueError("retry_backoff_seconds cannot be negative")
    if timeout_seconds is not None and timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    policy = TaskPolicy(
        retry_for=retry_for,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
        timeout_seconds=timeout_seconds,
    )

    def decorator(func: Callable[..., Any]) -> PlatformTask:
        @wraps(func)
        def reliable_function(*args: Any, **kwargs: Any):
            result_id = (
                kwargs.pop(PLATFORM_RESULT_ID_KWARG, None)
                or get_current_task_result_id()
            )
            idempotency_key = kwargs.pop(PLATFORM_IDEMPOTENCY_KWARG, None)
            kwargs.pop(PLATFORM_CORRELATION_ID_KWARG, None)
            task_name = f"{func.__module__}.{func.__qualname__}"
            if idempotency_key and not _claim_idempotency(
                task_name=task_name,
                key=idempotency_key,
                task_result_id=result_id or "unknown",
            ):
                return None

            attempt = 0
            while True:
                attempt += 1
                _record_attempt(result_id, attempt)
                try:
                    with _execution_timeout(policy.timeout_seconds):
                        result = func(*args, **kwargs)
                except policy.retry_for as error:
                    if attempt >= policy.max_attempts:
                        _mark_idempotency_failed(task_name, idempotency_key)
                        raise
                    _record_retry(result_id, attempt, error)
                    if policy.retry_backoff_seconds:
                        time.sleep(policy.retry_backoff_seconds * 2 ** (attempt - 1))
                    continue
                except Exception:
                    _mark_idempotency_failed(task_name, idempotency_key)
                    raise
                else:
                    _mark_idempotency_succeeded(task_name, idempotency_key)
                    return result

        registered = django_task(
            reliable_function,
            priority=priority,
            queue_name=queue_name,
            backend=backend,
            takes_context=takes_context,
        )
        _registered_task_paths.add(registered.module_path)
        return PlatformTask(registered, policy)

    if function is not None:
        return decorator(function)
    return decorator


def is_registered_platform_task(task: Task) -> bool:
    """Return whether a Django Task belongs to Platform Runtime."""
    return task.module_path in _registered_task_paths


def set_current_task_result_id(result_id: str):
    _current_task_result_id.set(result_id)


def reset_current_task_result_id() -> None:
    _current_task_result_id.set(None)


def get_current_task_result_id() -> str | None:
    return _current_task_result_id.get()


def enqueue_after_commit(
    task: PlatformTask,
    *args: Any,
    idempotency_key: str | None = None,
    **kwargs: Any,
) -> None:
    """Enqueue a task only after the surrounding transaction commits."""
    transaction.on_commit(
        lambda: task.enqueue(*args, idempotency_key=idempotency_key, **kwargs)
    )


def _claim_idempotency(*, task_name: str, key: str, task_result_id: str) -> bool:
    with transaction.atomic():
        try:
            record, created = TaskIdempotency.objects.select_for_update().get_or_create(
                task_name=task_name,
                key=key,
                defaults={
                    "status": TaskIdempotency.Status.IN_PROGRESS,
                    "task_result_id": task_result_id,
                },
            )
        except IntegrityError:
            record = TaskIdempotency.objects.select_for_update().get(
                task_name=task_name, key=key
            )
            created = False

        if not created and record.status in {
            TaskIdempotency.Status.IN_PROGRESS,
            TaskIdempotency.Status.SUCCEEDED,
        }:
            return False
        record.status = TaskIdempotency.Status.IN_PROGRESS
        record.task_result_id = task_result_id
        record.save(update_fields=["status", "task_result_id", "updated"])
        return True


def _mark_idempotency_succeeded(task_name: str, key: str | None) -> None:
    if key:
        TaskIdempotency.objects.filter(task_name=task_name, key=key).update(
            status=TaskIdempotency.Status.SUCCEEDED
        )


def _mark_idempotency_failed(task_name: str, key: str | None) -> None:
    if key:
        TaskIdempotency.objects.filter(task_name=task_name, key=key).update(
            status=TaskIdempotency.Status.FAILED
        )


def _record_attempt(result_id: str | None, attempt: int) -> None:
    result_id = result_id or get_current_task_result_id()
    if result_id:
        RuntimeLog.objects.filter(task_result_id=result_id).update(attempt=attempt)


def _record_retry(result_id: str | None, attempt: int, error: Exception) -> None:
    result_id = result_id or get_current_task_result_id()
    if result_id:
        RuntimeLog.objects.filter(task_result_id=result_id).update(
            status=RuntimeLog.Status.RETRYING,
            attempt=attempt,
            error_class=f"{type(error).__module__}.{type(error).__qualname__}",
        )


@contextmanager
def _execution_timeout(seconds: float | None):
    if (
        seconds is None
        or not hasattr(signal, "SIGALRM")
        or threading.current_thread() is not threading.main_thread()
    ):
        yield
        return

    def raise_timeout(signum, frame):
        raise TaskTimeoutError(f"Task exceeded {seconds} seconds")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
