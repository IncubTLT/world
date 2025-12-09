from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import ChatMessage, ChatRoom

User = get_user_model()


class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "display_name")


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = UserShortSerializer(read_only=True)

    class Meta:
        model = ChatMessage
        fields = ("id", "room", "sender", "text", "created_at")
        read_only_fields = ("id", "room", "sender", "created_at")


class ChatMessageCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000)


class ChatRoomSerializer(serializers.ModelSerializer):
    participants = UserShortSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ("id", "type", "name", "owner", "participants", "created_at", "updated_at", "last_message")
        read_only_fields = ("id", "owner", "created_at", "updated_at", "participants", "last_message")

    def get_last_message(self, obj: ChatRoom) -> dict | None:
        msg = obj.messages.select_related("sender").order_by("-created_at").first()  # pyright: ignore[reportAttributeAccessIssue]
        if not msg:
            return None
        return {
            "id": msg.id,
            "text": msg.text,
            "created_at": msg.created_at,
            "sender": {
                "id": msg.sender_id,
                "display_name": msg.sender.display_name,
            },
        }


class PrivateRoomCreateSerializer(serializers.Serializer):
    """
    Создание/получение личного чата.
    """
    partner_id = serializers.IntegerField()

    def validate_partner_id(self, value: int) -> int:
        request = self.context["request"]
        user = request.user
        if not user.is_authenticated:
            raise serializers.ValidationError("Требуется авторизация.")
        if value == user.id:
            raise serializers.ValidationError("Нельзя создавать личный чат с самим собой.")

        User = get_user_model()
        try:
            partner = User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь не найден.")
        self.context["partner"] = partner
        return value


class GroupRoomCreateSerializer(serializers.Serializer):
    """
    Создание группового чата.
    """
    name = serializers.CharField(max_length=255)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )

    def validate_participant_ids(self, value: list[int]) -> list[int]:
        request = self.context["request"]
        user = request.user
        ids = set(value)
        ids.add(user.id)

        User = get_user_model()
        users = list(User.objects.filter(id__in=ids))
        if len(users) != len(ids):
            raise serializers.ValidationError("Некоторые пользователи не найдены.")
        self.context["participants"] = users
        return list(ids)
