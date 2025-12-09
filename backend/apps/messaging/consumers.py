from __future__ import annotations

import asyncio
import json
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from config.async_redis import AsyncRedisClient
from django.contrib.auth import get_user_model

from .models import ChatMessage, ChatRoom

User = get_user_model()
STREAM_CHUNK_SIZE = 300


class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.redis_client = AsyncRedisClient.get_client()
        self.room: ChatRoom | None = None
        self.room_group_name: str | None = None
        self.message_count: int = 0

    # ---------- helpers (БД) ----------

    @database_sync_to_async
    def _get_room(self, room_id: str) -> ChatRoom:
        return ChatRoom.objects.get(id=room_id)

    @database_sync_to_async
    def _user_in_room(self, room: ChatRoom, user: User) -> bool:
        return room.participants.filter(pk=user.pk).exists()

    @database_sync_to_async
    def _save_message(self, user: User, text: str) -> ChatMessage:
        assert self.room is not None
        return ChatMessage.objects.create(
            room=self.room,
            sender=user,
            text=text,
        )

    # ---------- lifecycle ----------
    async def connect(self) -> None:
        # --- user из scope ---
        scope_user = self.scope.get("user")
        if scope_user is None or not getattr(scope_user, "is_authenticated", False):
            await self.close(code=4001)
            return

        user: User = scope_user  # после проверки можно типизировать

        # --- url_route из scope ---
        url_route: dict[str, Any] | None = self.scope.get("url_route")  # type: ignore
        if not url_route:
            await self.close(code=4000)  # нет данных маршрута
            return

        kwargs = url_route.get("kwargs") or {}
        room_id = kwargs.get("room_id")
        if room_id is None:
            await self.close(code=4000)
            return

        try:
            room = await self._get_room(room_id)
        except ChatRoom.DoesNotExist:
            await self.close(code=4004)
            return

        is_member = await self._user_in_room(room, user)
        if not is_member:
            await self.close(code=4003)  # forbidden
            return

        self.room = room
        self.room_group_name = f"chat_room_{room.id}"
        self.message_count = 0

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        self.room = room
        self.room_group_name = f"chat_room_{room.id}"
        self.message_count = 0

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        history_items = await self._get_last_messages_payload(limit=50)
        history_items.reverse()

        await self.send(
            text_data=json.dumps(
                {
                    "type": "history",
                    "items": history_items,
                }
            )
        )

    async def disconnect(self, code: int) -> None:
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive(
        self,
        text_data: str | None = None,
        bytes_data: bytes | None = None,
    ) -> None:
        if text_data is None:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error("Некорректный формат сообщения.")
            return

        message = payload.get("message")
        if not message:
            await self.send_error("Пустое сообщение.")
            return

        scope_user = self.scope.get("user")
        if scope_user is None:
            await self.send_error("Пользователь не определён.")
            return

        user: User = scope_user

        if self.room is None or self.room_group_name is None:
            await self.send_error("Комната не инициализирована.")
            return

        redis_key = f"chat:room:{self.room.id}:user:{user.id}:lock"
        time_limit = (
            (2, "ы") if getattr(user, "is_authenticated", False) else (5, ", для незарегистрированных пользователей")
        )

        if await self.redis_client.get(redis_key):
            await self.send_error(
                f"Запросы можно отправлять не чаще, чем раз в {time_limit[0]} секунд{time_limit[1]}."
            )
            return

        await self.redis_client.set(redis_key, "locked", ex=time_limit[0])

        self.message_count += 1

        await self._save_message(user, message)

        await self._broadcast_stream(user, message)

    async def chat_message(self, event: dict[str, Any]) -> None:
        """Отправка сообщения на клиент."""
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "display_name": event["display_name"],
                    "is_stream": event.get("is_stream", False),
                    "is_start": event.get("is_start", False),
                    "is_end": event.get("is_end", False),
                }
            )
        )

    async def send_error(self, error_message: str) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "message": error_message,
                    "error": True,
                }
            )
        )

    @database_sync_to_async
    def _get_last_messages_payload(self, limit: int = 50) -> list[dict]:
        """
        Возвращает последние limit сообщений комнаты в виде готовых dict'ов.
        """
        assert self.room is not None
        qs = (
            self.room.messages  # pyright: ignore[reportAttributeAccessIssue]
            .select_related("sender")
            .order_by("-created_at")[:limit]
        )
        items = []
        for m in qs:
            items.append(
                {
                    "id": m.id,
                    "text": m.text,
                    "display_name": m.sender.display_name,
                    "created_at": m.created_at.isoformat(),
                }
            )
        return items

    async def _broadcast_stream(self, user: User, message: str) -> None:
        """
        Отправляет сообщение в комнату:
        - если короткое — одним пакетом без стрима,
        - если длинное — режет на чанки и шлёт с флагами is_stream/is_start/is_end.
        """
        if not self.room_group_name:
            return

        text = message or ""
        if not text:
            return

        # короткое сообщение — старое поведение
        if len(text) <= STREAM_CHUNK_SIZE:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "message": text,
                    "display_name": user.display_name,
                    "is_stream": False,
                    "is_start": False,
                    "is_end": False,
                },
            )
            return

        # длинное сообщение — режем на чанки
        chunks = [
            text[i: i + STREAM_CHUNK_SIZE]
            for i in range(0, len(text), STREAM_CHUNK_SIZE)
        ]
        last_idx = len(chunks) - 1

        for idx, chunk in enumerate(chunks):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "message": chunk,
                    "display_name": user.display_name,
                    "is_stream": True,
                    "is_start": idx == 0,
                    "is_end": idx == last_idx,
                },
            )
            await asyncio.sleep(0.03)
