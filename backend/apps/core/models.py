import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from safedelete.config import DELETED_ONLY_VISIBLE, DELETED_VISIBLE
from safedelete.managers import SafeDeleteManager
from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel

from .managers import UserManager


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created"]

    def get_fields(self):
        return [
            (field.verbose_name, getattr(self, field.name))
            for field in self._meta.fields
        ]


class SafeDeleteBaseModel(SafeDeleteModel, BaseModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    class Meta:
        abstract = True


class PresentationMode(models.TextChoices):
    DEFAULT = "default", "Default"
    DASHBOARD = "dashboard", "Dashboard"
    MOBILE = "mobile", "Mobile"


class OrganizationSettings(BaseModel):
    """Singleton organization identity used by the dashboard and reports."""

    key = models.CharField(max_length=20, unique=True, default="default", editable=False)
    organization_name = models.CharField(max_length=150, default="djaapp")
    logo = models.FileField(upload_to="organization/", blank=True, null=True)
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    mobile_presentation_enabled = models.BooleanField(default=False)
    presentation_mode = models.CharField(
        max_length=20,
        choices=PresentationMode.choices,
        default=PresentationMode.DEFAULT,
    )

    class Meta:
        verbose_name = "organization settings"
        verbose_name_plural = "organization settings"

    def __str__(self):
        return self.organization_name


class AllObjectsManager(SafeDeleteManager):
    _safedelete_visibility = DELETED_VISIBLE


class DeletedObjectsManager(SafeDeleteManager):
    _safedelete_visibility = DELETED_ONLY_VISIBLE


class User(SafeDeleteBaseModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    profile_name = models.CharField(max_length=150, blank=True)
    profile_photo = models.FileField(
        upload_to="profile_photos/", blank=True, null=True
    )

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    presentation_mode = models.CharField(
        max_length=20,
        choices=PresentationMode.choices,
        default=PresentationMode.DEFAULT,
    )

    objects = UserManager()
    all_objects = AllObjectsManager()
    deleted_objects = DeletedObjectsManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["-created"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.profile_name or self.email

    def get_short_name(self):
        return self.profile_name or self.email


class Role(SafeDeleteBaseModel):
    name = models.CharField(max_length=50, unique=True)
    level = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    presentation_mode_policy = models.CharField(
        max_length=20,
        choices=PresentationMode.choices,
        default=PresentationMode.DEFAULT,
    )
    permissions = models.ManyToManyField("Permission", blank=True, related_name="roles")

    objects = SafeDeleteManager()
    all_objects = AllObjectsManager()
    deleted_objects = DeletedObjectsManager()

    class Meta:
        ordering = ["-level"]
        verbose_name = "role"
        verbose_name_plural = "roles"

    def __str__(self):
        return self.name

    def has_higher_rank_than(self, other_role):
        return self.level > other_role.level


class Permission(SafeDeleteBaseModel):
    resource = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    objects = SafeDeleteManager()
    all_objects = AllObjectsManager()
    deleted_objects = DeletedObjectsManager()

    class Meta:
        unique_together = ["resource", "action"]
        ordering = ["resource", "action"]
        verbose_name = "permission"
        verbose_name_plural = "permissions"

    def __str__(self):
        return f"{self.resource}:{self.action}"


class UserRole(SafeDeleteBaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_users")
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_roles",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    objects = SafeDeleteManager()
    all_objects = AllObjectsManager()
    deleted_objects = DeletedObjectsManager()

    class Meta:
        unique_together = ["user", "role"]
        ordering = ["-assigned_at"]
        verbose_name = "user role"
        verbose_name_plural = "user roles"

    def __str__(self):
        return f"{self.user.email} - {self.role.name}"
