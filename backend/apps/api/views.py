"""API Views for authentication, user management, and role management."""

from django.contrib.auth import logout
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.selectors import role_get, roles_list, user_role_get, users_list
from apps.core.services import assign_role_to_user, remove_role_from_user, user_delete

from .permissions import (
    CanAssignRoles,
    CanManageUsers,
    CanViewUsers,
)
from .serializers import (
    CustomTokenObtainPairSerializer,
    ErrorResponseSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    RefreshResponseSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserRoleSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


class LoginRateThrottle(AnonRateThrottle):
    """Rate limiter for login attempts: 5 per minute."""

    rate = "5/minute"


@extend_schema(
    tags=["Authentication"],
    summary="Login",
    description="Authenticate user with email, phone, or employee_id.",
    request=LoginRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=LoginResponseSerializer, description="Login successful"
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Invalid credentials"
        ),
        429: OpenApiResponse(
            response=ErrorResponseSerializer, description="Too many login attempts"
        ),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    """Login endpoint that accepts identifier and password."""
    serializer = CustomTokenObtainPairSerializer(
        data=request.data, context={"request": request}
    )

    if not serializer.is_valid():
        return Response(
            {"detail": "Invalid credentials", "errors": serializer.errors},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Authentication"],
    summary="Logout",
    description="Logout user and blacklist refresh token.",
    responses={
        200: OpenApiResponse(description="Logout successful"),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized"
        ),
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout endpoint that blacklists the refresh token."""
    refresh_token = request.data.get("refresh")

    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass

    logout(request)

    return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Authentication"],
    summary="Refresh Token",
    description="Refresh access token using refresh token.",
    responses={
        200: OpenApiResponse(
            response=RefreshResponseSerializer, description="Token refreshed"
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Invalid refresh token"
        ),
    },
)
class CustomTokenRefreshView(TokenRefreshView):
    """Custom token refresh view with additional response data."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            response.data["message"] = "Token refreshed successfully"
        return response


@extend_schema(
    tags=["Authentication"],
    summary="Get Current User",
    description="Get information about the currently authenticated user.",
    responses={
        200: OpenApiResponse(response=UserSerializer, description="User info"),
        401: OpenApiResponse(
            response=ErrorResponseSerializer, description="Unauthorized"
        ),
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Get current user information."""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@extend_schema(
    tags=["Users"],
    summary="User Management",
    description="CRUD operations for user management.",
)
class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user management with soft delete support."""

    queryset = users_list()
    serializer_class = UserSerializer
    lookup_field = "pk"

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsAuthenticated, CanViewUsers]
        elif self.action in ["assign_role", "remove_role"]:
            permission_classes = [IsAuthenticated, CanAssignRoles]
        else:
            permission_classes = [IsAuthenticated, CanManageUsers]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        filters = {}
        email = self.request.query_params.get("email")
        if email:
            filters["email"] = email

        is_staff = self.request.query_params.get("is_staff")
        if is_staff is not None:
            filters["is_staff"] = is_staff.lower() == "true"

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            filters["is_active"] = is_active.lower() == "true"

        return users_list(filters=filters)

    def perform_destroy(self, instance):
        """Perform soft delete instead of hard delete."""
        user_delete(user=instance)

    @extend_schema(
        summary="List Users",
        description="Get paginated list of users with optional filters.",
        responses={200: OpenApiResponse(response=UserSerializer(many=True))},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create User",
        description="Create a new user account.",
        request=UserCreateSerializer,
        responses={
            201: OpenApiResponse(response=UserSerializer, description="User created"),
            400: OpenApiResponse(
                response=ErrorResponseSerializer, description="Invalid data"
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Get User",
        description="Get detailed information about a specific user.",
        responses={
            200: OpenApiResponse(response=UserSerializer),
            404: OpenApiResponse(
                response=ErrorResponseSerializer, description="User not found"
            ),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update User",
        description="Update user information (full update).",
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(response=UserSerializer),
            400: OpenApiResponse(
                response=ErrorResponseSerializer, description="Invalid data"
            ),
            404: OpenApiResponse(
                response=ErrorResponseSerializer, description="User not found"
            ),
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partial Update User",
        description="Update user information (partial update).",
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(response=UserSerializer),
            400: OpenApiResponse(
                response=ErrorResponseSerializer, description="Invalid data"
            ),
            404: OpenApiResponse(
                response=ErrorResponseSerializer, description="User not found"
            ),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete User",
        description="Soft delete a user account.",
        responses={
            204: OpenApiResponse(description="User deleted"),
            404: OpenApiResponse(
                response=ErrorResponseSerializer, description="User not found"
            ),
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        tags=["Roles"],
        summary="Assign Role to User",
        description="Assign a role to a user.",
        request=UserRoleSerializer,
        responses={
            201: OpenApiResponse(
                response=UserRoleSerializer, description="Role assigned"
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer, description="Invalid data"
            ),
            404: OpenApiResponse(
                response=ErrorResponseSerializer, description="User or role not found"
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, CanAssignRoles],
        url_path="roles",
    )
    def assign_role(self, request, pk=None):
        """Assign a role to a user."""
        user = self.get_object()
        role_id = request.data.get("role_id")

        if not role_id:
            return Response(
                {"detail": "role_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            role = role_get(role_id=role_id)
        except (TypeError, ValueError):
            role = None
        if role is None:
            return Response(
                {"detail": "Role not found."}, status=status.HTTP_404_NOT_FOUND
            )

        success = assign_role_to_user(user=user, role=role, assigned_by=request.user)

        if not success:
            return Response(
                {"detail": "Role is already assigned to this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_role = user_role_get(user=user, role=role)
        serializer = UserRoleSerializer(user_role)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Roles"],
        summary="Remove Role from User",
        description="Remove a role from a user.",
        responses={
            204: OpenApiResponse(description="Role removed"),
            404: OpenApiResponse(
                response=ErrorResponseSerializer, description="User or role not found"
            ),
        },
    )
    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[IsAuthenticated, CanAssignRoles],
        url_path="roles/(?P<role_id>[^/.]+)",
    )
    def remove_role(self, request, pk=None, role_id=None):
        """Remove a role from a user."""
        user = self.get_object()

        try:
            role = role_get(role_id=role_id)
        except (TypeError, ValueError):
            role = None
        if role is None:
            return Response(
                {"detail": "Role not found."}, status=status.HTTP_404_NOT_FOUND
            )

        success = remove_role_from_user(user=user, role=role)

        if not success:
            return Response(
                {"detail": "Role is not assigned to this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Roles"],
    summary="Role Management",
    description="CRUD operations for roles.",
)
class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing roles (read-only for regular users)."""

    queryset = roles_list()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return roles_list()


@extend_schema(
    tags=["Health"],
    summary="Health Check",
    description="Check if the API is running.",
    responses={200: OpenApiResponse(description="API is healthy")},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint."""
    return Response(
        {"status": "ok", "message": "API is running"}, status=status.HTTP_200_OK
    )
