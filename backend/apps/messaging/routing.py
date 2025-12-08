from __future__ import annotations

from typing import Any, Callable, cast

from django.urls import re_path

from .consumers import ChatConsumer

websocket_urlpatterns: list[Any] = [
    re_path(
        r"^ws/chat/(?P<room_id>[0-9a-f-]+)/$",
        cast(Callable[..., Any], ChatConsumer.as_asgi()),
    )
]
