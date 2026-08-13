from django.apps import AppConfig


class PlatformRuntimeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform_runtime"
    label = "platform_runtime"

    def ready(self):
        from auditlog.registry import auditlog

        from .models import WebhookEvent

        auditlog.register(WebhookEvent, exclude_fields=["safe_payload"])
        from . import observability, signals  # noqa: F401
