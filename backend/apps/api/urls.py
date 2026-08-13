"""URL configuration for API endpoints."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomTokenRefreshView,
    RoleViewSet,
    UserViewSet,
    health_check,
    login_view,
    logout_view,
    me_view,
)

app_name = "api"

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"roles", RoleViewSet, basename="role")

urlpatterns = [
    path("auth/login/", login_view, name="login"),
    path("auth/logout/", logout_view, name="logout"),
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", me_view, name="me"),
    path("health/", health_check, name="health_check"),
]

urlpatterns += router.urls
