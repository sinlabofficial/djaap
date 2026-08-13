"""DRF Serializers for API endpoints."""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import Permission, Role, User, UserRole
from apps.core.selectors import role_get
from apps.core.services import user_create, user_update


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer that accepts identifier (email/phone/employee_id)."""

    username_field = "identifier"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields["password"] = serializers.CharField(
            write_only=True, style={"input_type": "password"}
        )

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        identifier = attrs.get("identifier")
        password = attrs.get("password")

        if not identifier or not password:
            raise serializers.ValidationError(
                'Must include "identifier" and "password".', code="authorization"
            )

        user = authenticate(
            request=self.context.get("request"),
            identifier=identifier,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError(
                "Unable to log in with provided credentials.", code="authorization"
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "User account is disabled.", code="authorization"
            )

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        }


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with role information."""

    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "employee_id",
            "is_staff",
            "is_active",
            "is_superuser",
            "roles",
            "created",
            "updated",
        ]
        read_only_fields = [
            "id",
            "is_superuser",
            "created",
            "updated",
        ]

    def get_roles(self, obj):
        return [
            {
                "id": str(user_role.role.id),
                "name": user_role.role.name,
                "level": user_role.role.level,
            }
            for user_role in obj.user_roles.filter(deleted__isnull=True).select_related(
                "role"
            )
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users."""

    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "employee_id",
            "password",
            "password_confirm",
            "is_staff",
            "is_active",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        if data.get("password") != data.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        return user_create(password=password, **validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing users."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "employee_id",
            "is_staff",
            "is_active",
        ]
        read_only_fields = ["id"]

    def update(self, instance, validated_data):
        return user_update(user=instance, **validated_data)


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model with permissions."""

    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "level",
            "description",
            "permissions",
            "created",
            "updated",
        ]
        read_only_fields = ["id", "created", "updated"]

    def get_permissions(self, obj):
        return [
            {
                "id": str(perm.id),
                "resource": perm.resource,
                "action": perm.action,
            }
            for perm in obj.permissions.filter(deleted__isnull=True)
        ]


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission model."""

    class Meta:
        model = Permission
        fields = [
            "id",
            "resource",
            "action",
            "description",
            "created",
            "updated",
        ]
        read_only_fields = ["id", "created", "updated"]


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for UserRole model (role assignments)."""

    role = RoleSerializer(read_only=True)
    role_id = serializers.UUIDField(write_only=True)
    assigned_by = UserSerializer(read_only=True)

    class Meta:
        model = UserRole
        fields = [
            "id",
            "user",
            "role",
            "role_id",
            "assigned_by",
            "assigned_at",
        ]
        read_only_fields = ["id", "assigned_at", "user"]

    def validate_role_id(self, value):
        try:
            role = role_get(role_id=value)
        except (TypeError, ValueError):
            role = None
        if role is None:
            raise serializers.ValidationError("Role does not exist.")
        return value


class LoginRequestSerializer(serializers.Serializer):
    """Serializer for login request validation."""

    identifier = serializers.CharField(help_text="Email, phone number, or employee ID")
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}, help_text="User password"
    )


class LoginResponseSerializer(serializers.Serializer):
    """Serializer for login response."""

    refresh = serializers.CharField(help_text="JWT refresh token")
    access = serializers.CharField(help_text="JWT access token")
    user = UserSerializer(help_text="User information")


class RefreshResponseSerializer(serializers.Serializer):
    """Serializer for token refresh response."""

    access = serializers.CharField(help_text="New JWT access token")
    refresh = serializers.CharField(help_text="New JWT refresh token")
    message = serializers.CharField(help_text="Status message")


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""

    detail = serializers.CharField(help_text="Error message")
    code = serializers.CharField(help_text="Error code", required=False)


class UserListSerializer(serializers.Serializer):
    """Serializer for paginated user list response."""

    count = serializers.IntegerField(help_text="Total number of users")
    next = serializers.URLField(help_text="Next page URL", required=False)
    previous = serializers.URLField(help_text="Previous page URL", required=False)
    results = UserSerializer(many=True, help_text="List of users")
