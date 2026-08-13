from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from auditlog.registry import auditlog

        from .models import OrganizationSettings, Permission, Role, User, UserRole

        auditlog.register(User, exclude_fields=["password"])
        auditlog.register(Role)
        auditlog.register(Permission)
        auditlog.register(UserRole)
        auditlog.register(OrganizationSettings)
