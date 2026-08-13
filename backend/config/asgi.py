import os

from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

if settings.REALTIME_ENABLED:
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.core.asgi import get_asgi_application

    from apps.platform_runtime.routing import websocket_urlpatterns

    application = ProtocolTypeRouter(
        {
            "http": get_asgi_application(),
            "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
        }
    )
else:
    from django.core.asgi import get_asgi_application

    application = get_asgi_application()
