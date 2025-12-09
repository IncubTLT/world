from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ChatMessage, ChatRoom
from .serializers import (ChatMessageCreateSerializer, ChatMessageSerializer,
                          ChatRoomSerializer, GroupRoomCreateSerializer,
                          PrivateRoomCreateSerializer)

User = get_user_model()


class ChatRoomViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet только для чтения + кастомные экшены для создания комнат и сообщений.
    """

    serializer_class = ChatRoomSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        user = self.request.user
        if not user.is_authenticated:
            return ChatRoom.objects.none()
        # показываем только комнаты, где пользователь участник
        return (
            ChatRoom.objects.filter(participants=user)
            .prefetch_related("participants", "messages__sender")
            .order_by("-updated_at")
        )

    @extend_schema(
        summary="Список комнат пользователя",
        description="Возвращает все чаты (личные и групповые), в которых состоит текущий пользователь.",
        tags=["Messaging"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Детали комнаты",
        description="Информация о комнате и участниках (только если текущий пользователь состоит в комнате).",
        tags=["Messaging"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # --- Личные чаты ---

    @extend_schema(
        summary="Создать или получить личный чат",
        description=(
            "Если личный чат между текущим пользователем и partner_id уже существует — "
            "возвращается он. Иначе создаётся новый."
        ),
        request=PrivateRoomCreateSerializer,
        responses={200: ChatRoomSerializer, 201: ChatRoomSerializer},
        tags=["Messaging"],
    )
    @action(detail=False, methods=["post"], url_path="private", permission_classes=[IsAuthenticated])
    def private(self, request):
        serializer = PrivateRoomCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        partner: User = serializer.context["partner"]
        user: User = request.user

        # ищем существующую личную комнату (оба участника)
        room_qs = (
            ChatRoom.objects.filter(type=ChatRoom.RoomType.PRIVATE)
            .filter(participants=user)
            .filter(participants=partner)
            .distinct()
        )
        created = False
        if room_qs.exists():
            room = room_qs.first()
        else:
            room = ChatRoom.objects.create(
                type=ChatRoom.RoomType.PRIVATE,
                owner=user,
            )
            room.participants.set([user, partner])
            created = True

        data = ChatRoomSerializer(room, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    # --- Групповые чаты ---
    @extend_schema(
        summary="Создать групповую комнату",
        description="Создаёт групповой чат и добавляет участников.",
        request=GroupRoomCreateSerializer,
        responses={201: ChatRoomSerializer},
        tags=["Messaging"],
    )
    @action(detail=False, methods=["post"], url_path="group", permission_classes=[IsAuthenticated])
    def group(self, request):
        serializer = GroupRoomCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        participants: list[User] = serializer.context["participants"]
        user: User = request.user

        room = ChatRoom.objects.create(
            type=ChatRoom.RoomType.GROUP,
            name=serializer.validated_data["name"],  # type: ignore
            owner=user,
        )
        room.participants.set(participants)

        data = ChatRoomSerializer(room, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)

    # --- История и отправка сообщений в комнате ---

    @extend_schema(
        summary="История сообщений комнаты",
        description=(
            "Возвращает сообщения в комнате с пагинацией. Доступно только участникам комнаты.\n\n"
            "По умолчанию сообщения отсортированы по дате создания (по возрастанию). "
            "Используется стандартная пагинация DRF."
        ),
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                required=False,
                description="Номер страницы (стандартный PageNumberPagination).",
            )
        ],
        responses={200: ChatMessageSerializer(many=True)},
        tags=["Messaging"],
    )
    @action(detail=True, methods=["get"], url_path="messages", permission_classes=[IsAuthenticated])
    def messages(self, request, pk=None):
        room: ChatRoom = self.get_object()
        qs = room.messages.select_related("sender").order_by("created_at")

        page = self.paginate_queryset(qs)
        if page is not None:
            ser = ChatMessageSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(ser.data)

        ser = ChatMessageSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)

    @extend_schema(
        summary="Отправить сообщение в комнату (HTTP)",
        description=(
            "Отправляет сообщение в комнату от имени текущего пользователя через HTTP. "
            "Сообщение сохраняется в БД, а realtime-доставка осуществляется через WebSocket консумер."
        ),
        request=ChatMessageCreateSerializer,
        responses={201: ChatMessageSerializer},
        tags=["Messaging"],
    )
    @messages.mapping.post  # type: ignore
    def send_message(self, request, pk=None):
        room: ChatRoom = self.get_object()
        serializer = ChatMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        msg = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            text=serializer.validated_data["text"],
        )
        room.save(update_fields=["updated_at"])
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"chat_room_{room.id}",
                {
                    "type": "chat.message",
                    "message": msg.text,
                    "display_name": request.user.display_name,
                    "is_stream": False,
                    "is_start": False,
                    "is_end": False,
                },
            )

        out = ChatMessageSerializer(msg, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)
