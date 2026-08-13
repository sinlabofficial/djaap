import re
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.core.selectors import user_has_permission

from .realtime import _group_name


class DashboardRealtimeConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        permission = parse_qs(self.scope.get("query_string", b"").decode()).get(
            "permission", [""]
        )[0]
        if permission and not await self._can_subscribe(user, permission):
            await self.close(code=4403)
            return
        self.group_name = _group_name(permission)
        self.subscription_permission = permission
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def realtime_event(self, event):
        if self.subscription_permission:
            user = self.scope.get("user")
            if not user or not await self._can_subscribe(user, self.subscription_permission):
                await self.close(code=4403)
                return
        await self.send_json(event["event"])

    @database_sync_to_async
    def _can_subscribe(self, user, permission: str) -> bool:
        if not re.fullmatch(r"[a-z][a-z0-9_]*:[a-z][a-z0-9_]*", permission):
            return False
        return user.is_superuser or user_has_permission(user=user, permission=permission)
