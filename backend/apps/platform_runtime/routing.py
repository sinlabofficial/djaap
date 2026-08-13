from django.urls import re_path

from .consumers import DashboardRealtimeConsumer

websocket_urlpatterns = [
    re_path(r"^ws/realtime/$", DashboardRealtimeConsumer.as_asgi()),
]
