from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.platform_runtime.http import realtime_events
from apps.platform_runtime.views import inbound_webhook

if settings.API_ENABLED:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )

urlpatterns = [
    path(
        "",
        RedirectView.as_view(pattern_name="dashboard:login", permanent=False),
        name="root",
    ),
    path("admin/", admin.site.urls),
    path("webhooks/<str:provider>/", inbound_webhook, name="inbound-webhook"),
    path("dashboard/realtime/events/", realtime_events, name="realtime-events"),
]

urlpatterns += [
    path("dashboard/example/", include("apps.example.urls", namespace="example")),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("impersonate/", include("impersonate.urls")),
]

if settings.API_ENABLED:
    urlpatterns.append(path("api/", include("apps.api.urls", namespace="api")))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.API_ENABLED:
    urlpatterns += [
        path("api/docs/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/swagger/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"
        ),
    ]
