from __future__ import annotations

import json

import pytest
from apps.messaging.models import ChatMessage, ChatRoom
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_create_private_room_and_reuse(api_client: APIClient, regular_user):
    """
    POST /api/messaging/rooms/private/:
    - создаёт личный чат между двумя пользователями,
    - повторный вызов возвращает тот же room.id.
    """
    user1 = regular_user
    user2 = User.objects.create_user(email="friend@example.com")

    api_client.force_authenticate(user=user1)

    url = "/api/messaging/rooms/private/"

    # 1-й вызов — создаём
    resp1 = api_client.post(url, {"partner_id": user2.id}, format="json")
    assert resp1.status_code == 201

    room_id = resp1.data["id"]
    room = ChatRoom.objects.get(id=room_id)
    participants_ids = set(room.participants.values_list("id", flat=True))
    assert participants_ids == {user1.id, user2.id}

    # 2-й вызов — должен вернуть тот же room
    resp2 = api_client.post(url, {"partner_id": user2.id}, format="json")
    assert resp2.status_code == 200
    assert resp2.data["id"] == room_id


@pytest.mark.django_db
def test_private_room_cannot_be_created_with_self(api_client: APIClient, regular_user):
    """
    Нельзя создавать личный чат с самим собой.
    """
    api_client.force_authenticate(user=regular_user)
    url = "/api/messaging/rooms/private/"


    resp = api_client.post(url, {"partner_id": regular_user.id}, format="json")
    assert resp.status_code == 400

    # resp.data = {"partner_id": [ErrorDetail("Нельзя создавать личный чат с самим собой.", ...)]}
    errors = resp.data.get("partner_id", [])
    text = " ".join(str(e) for e in errors).lower()
    assert "нельзя" in text


@pytest.mark.django_db
def test_private_room_partner_must_exist(api_client: APIClient, regular_user):
    """
    При создании личного чата partner_id должен существовать.
    """
    api_client.force_authenticate(user=regular_user)
    url = "/api/messaging/rooms/private/"

    resp = api_client.post(url, {"partner_id": 999999}, format="json")
    assert resp.status_code == 400

    errors = resp.data.get("partner_id", [])
    text = " ".join(str(e) for e in errors).lower()
    assert "не найден" in text


@pytest.mark.django_db
def test_create_group_room(api_client: APIClient, regular_user):
    """
    POST /api/messaging/rooms/group/ создаёт групповой чат
    с указанными участниками + создатель всегда участник.
    """
    user1 = regular_user
    user2 = User.objects.create_user(email="user2@example.com")
    user3 = User.objects.create_user(email="user3@example.com")

    api_client.force_authenticate(user=user1)
    url = "/api/messaging/rooms/group/"

    resp = api_client.post(
        url,
        {"name": "Our group", "participant_ids": [user2.id, user3.id]},
        format="json",
    )
    assert resp.status_code == 201

    room_id = resp.data["id"]
    room = ChatRoom.objects.get(id=room_id)

    participants_ids = set(room.participants.values_list("id", flat=True))
    # создатель + указанные участники
    assert participants_ids == {user1.id, user2.id, user3.id}
    assert room.type == ChatRoom.RoomType.GROUP


@pytest.mark.django_db
def test_create_group_room_requires_participants(api_client: APIClient, regular_user):
    """
    Создание группового чата без участников (кроме создателя) должно падать с 400.
    """
    api_client.force_authenticate(user=regular_user)
    url = "/api/messaging/rooms/group/"

    resp = api_client.post(
        url,
        {"name": "Solo group", "participant_ids": []},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_list_user_rooms_only_own(api_client: APIClient, regular_user):
    """
    GET /api/messaging/rooms/ возвращает только те комнаты,
    где пользователь является участником.
    """
    user1 = regular_user
    user2 = User.objects.create_user(email="other@example.com")

    # комната только user1
    room1 = ChatRoom.objects.create(type=ChatRoom.RoomType.PRIVATE, owner=user1)
    room1.participants.set([user1])

    # комната user2 без user1
    room2 = ChatRoom.objects.create(type=ChatRoom.RoomType.PRIVATE, owner=user2)
    room2.participants.set([user2])

    api_client.force_authenticate(user=user1)

    url = "/api/messaging/rooms/"
    resp = api_client.get(url)
    assert resp.status_code == 200

    # PageNumberPagination -> results
    returned_ids = {str(r["id"]) for r in resp.data["results"]}
    assert str(room1.id) in returned_ids
    assert str(room2.id) not in returned_ids


@pytest.mark.django_db
def test_room_messages_history_and_order(api_client: APIClient, regular_user):
    """
    GET /api/messaging/rooms/{id}/messages/:
    - доступен только участнику,
    - сообщения приходят в хронологическом порядке.
    """
    user1 = regular_user
    user2 = User.objects.create_user(email="partner@example.com")

    room = ChatRoom.objects.create(type=ChatRoom.RoomType.PRIVATE, owner=user1)
    room.participants.set([user1, user2])

    # создаём несколько сообщений
    ChatMessage.objects.create(room=room, sender=user1, text="hello")
    ChatMessage.objects.create(room=room, sender=user2, text="hi")
    ChatMessage.objects.create(room=room, sender=user1, text="how are you")

    api_client.force_authenticate(user=user1)
    url = f"/api/messaging/rooms/{room.id}/messages/"
    resp = api_client.get(url)
    assert resp.status_code == 200

    results = resp.data["results"]
    assert len(results) == 3
    texts = [m["text"] for m in results]
    assert texts == ["hello", "hi", "how are you"]  # по created_at


@pytest.mark.django_db
def test_room_messages_forbidden_for_non_participant(api_client: APIClient, regular_user):
    """
    Пользователь, не входящий в комнату, не должен получить историю.
    Ожидаем 404 (так безопаснее, чем 403).
    """
    user1 = regular_user
    user2 = User.objects.create_user(email="participant@example.com")
    stranger = User.objects.create_user(email="stranger@example.com")

    room = ChatRoom.objects.create(type=ChatRoom.RoomType.PRIVATE, owner=user1)
    room.participants.set([user1, user2])

    ChatMessage.objects.create(room=room, sender=user1, text="secret")

    api_client.force_authenticate(user=stranger)
    url = f"/api/messaging/rooms/{room.id}/messages/"
    resp = api_client.get(url)

    assert resp.status_code == 404


@pytest.mark.django_db
def test_send_message_http_creates_message_and_broadcasts(api_client: APIClient, regular_user, monkeypatch):
    """
    POST /api/messaging/rooms/{id}/messages/:
    - создаёт ChatMessage,
    - обновляет комнату,
    - отправляет событие в channel_layer.group_send.
    """
    user1 = regular_user
    user2 = User.objects.create_user(email="partner@example.com")

    room = ChatRoom.objects.create(type=ChatRoom.RoomType.PRIVATE, owner=user1)
    room.participants.set([user1, user2])

    api_client.force_authenticate(user=user1)

    # Заглушка для channel_layer
    class DummyLayer:
        def __init__(self):
            self.calls: list[tuple[str, dict]] = []

        async def group_send(self, group: str, event: dict) -> None:
            self.calls.append((group, event))

    dummy_layer = DummyLayer()

    # Патчим get_channel_layer в модуле, где определён ChatRoomViewSet
    import apps.messaging.views as messaging_views

    def fake_get_channel_layer():
        return dummy_layer

    monkeypatch.setattr(messaging_views, "get_channel_layer", fake_get_channel_layer)

    url = f"/api/messaging/rooms/{room.id}/messages/"
    resp = api_client.post(url, {"text": "hello via http"}, format="json")
    assert resp.status_code == 201

    # сообщение создано в БД
    assert ChatMessage.objects.filter(room=room, text="hello via http").exists()

    # был вызван group_send с нужными полями
    assert len(dummy_layer.calls) == 1
    group, event = dummy_layer.calls[0]
    assert group == f"chat_room_{room.id}"
    assert event["message"] == "hello via http"
    assert event["display_name"] == user1.display_name
    assert event["is_stream"] is False
    assert event["is_start"] is False
    assert event["is_end"] is False


@pytest.mark.django_db
def test_send_message_http_forbidden_for_non_participant(api_client: APIClient, regular_user):
    """
    Неучастник комнаты не может отправлять в неё сообщения по HTTP.
    Ожидаем 404 (комната просто не найдётся в queryset).
    """
    user1 = regular_user
    stranger = User.objects.create_user(email="stranger@example.com")

    room = ChatRoom.objects.create(type=ChatRoom.RoomType.PRIVATE, owner=user1)
    room.participants.set([user1])

    api_client.force_authenticate(user=stranger)

    url = f"/api/messaging/rooms/{room.id}/messages/"
    resp = api_client.post(url, {"text": "intruder"}, format="json")
    assert resp.status_code == 404
