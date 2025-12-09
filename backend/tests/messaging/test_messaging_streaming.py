from __future__ import annotations

import json

import pytest
from apps.messaging.consumers import STREAM_CHUNK_SIZE, ChatConsumer
from django.contrib.auth import get_user_model

User = get_user_model()


class DummyLayer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def group_send(self, group: str, event: dict) -> None:
        self.calls.append((group, event))


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_broadcast_stream_short_message_uses_single_event(regular_user):
    """
    Короткое сообщение (<= STREAM_CHUNK_SIZE) отправляется одним событием
    без стрим-флагов.
    """
    user = regular_user
    consumer = ChatConsumer()
    consumer.room_group_name = "chat_room_test"
    consumer.channel_layer = DummyLayer()

    msg_text = "hello"
    await consumer._broadcast_stream(user, msg_text)

    calls = consumer.channel_layer.calls
    assert len(calls) == 1
    group, event = calls[0]

    assert group == "chat_room_test"
    assert event["message"] == msg_text
    assert event["display_name"] == user.display_name
    assert event["is_stream"] is False
    assert event["is_start"] is False
    assert event["is_end"] is False


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_broadcast_stream_long_message_split_to_chunks(regular_user):
    """
    Длинное сообщение режется на чанки:
    - количество событий соответствует количеству чанков,
    - выставляются корректные is_stream / is_start / is_end.
    """
    user = regular_user
    consumer = ChatConsumer()
    consumer.room_group_name = "chat_room_test"
    consumer.channel_layer = DummyLayer()

    long_text = "x" * (STREAM_CHUNK_SIZE * 2 + 10)  # точно больше двух чанков
    await consumer._broadcast_stream(user, long_text)

    calls = consumer.channel_layer.calls
    assert len(calls) == 3  # 2 полных чанка + 1 остаток

    total = ""
    for idx, (group, event) in enumerate(calls):
        assert group == "chat_room_test"
        assert event["display_name"] == user.display_name
        assert event["is_stream"] is True

        if idx == 0:
            assert event["is_start"] is True
            assert event["is_end"] is False
        elif idx == len(calls) - 1:
            assert event["is_start"] is False
            assert event["is_end"] is True
        else:
            assert event["is_start"] is False
            assert event["is_end"] is False

        total += event["message"]

    # При склейке всех чанков получаем исходный текст
    assert total == long_text


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_broadcast_stream_empty_message_does_nothing(regular_user):
    """
    Пустое сообщение не должно ничего отправлять в channel_layer.
    """
    user = regular_user
    consumer = ChatConsumer()
    consumer.room_group_name = "chat_room_test"
    consumer.channel_layer = DummyLayer()

    await consumer._broadcast_stream(user, "")

    assert consumer.channel_layer.calls == []


@pytest.mark.asyncio
async def test_chat_message_sends_correct_json_payload():
    """
    chat_message сериализует событие в JSON с нужными полями и флагами.
    """
    consumer = ChatConsumer()

    sent: dict[str, str | bytes | None] = {}

    async def fake_send(*, text_data=None, bytes_data=None):
        sent["text_data"] = text_data
        sent["bytes_data"] = bytes_data

    # подменяем send на заглушку
    consumer.send = fake_send  # type: ignore[assignment]

    event = {
        "message": "Hello streamed",
        "display_name": "Tester",
        "is_stream": True,
        "is_start": True,
        "is_end": False,
    }

    await consumer.chat_message(event)

    assert "text_data" in sent
    payload = json.loads(sent["text_data"])  # type: ignore[arg-type]

    assert payload["message"] == "Hello streamed"
    assert payload["display_name"] == "Tester"
    assert payload["is_stream"] is True
    assert payload["is_start"] is True
    assert payload["is_end"] is False
