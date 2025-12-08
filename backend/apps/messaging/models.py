from __future__ import annotations
import uuid
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.db import models

from apps.utils.models import Create, CreateUpdater

User = get_user_model()


class ChatRoom(CreateUpdater):
    class RoomType(models.TextChoices):
        PRIVATE = "private", _("Личный чат")
        GROUP = "group", _("Групповой чат")

    id = models.UUIDField(
        _("ID комнаты"),
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    type = models.CharField(
        _("Тип комнаты"),
        max_length=16,
        choices=RoomType.choices,
    )
    name = models.CharField(
        _("Название"),
        max_length=255,
        blank=True,
        help_text=_("Имя используется только для групповых комнат."),
    )
    owner = models.ForeignKey(
        User,
        verbose_name=_("Владелец"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_chat_rooms",
    )
    participants = models.ManyToManyField(
        User,
        verbose_name=_("Участники"),
        through="ChatRoomParticipant",
        related_name="chat_rooms",
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = _("Комната чата")
        verbose_name_plural = _("Комнаты чата")

    def __str__(self) -> str:
        if self.type == self.RoomType.PRIVATE:
            return _("Личный чат %(id)s") % {"id": self.id}
        return self.name or _("Групповой чат %(id)s") % {"id": self.id}


class ChatRoomParticipant(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        verbose_name=_("Комната"),
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        User,
        verbose_name=_("Пользователь"),
        on_delete=models.CASCADE,
        related_name="chat_memberships",
    )
    is_admin = models.BooleanField(_("Администратор"), default=False)
    joined_at = models.DateTimeField(_("Дата вступления"), auto_now_add=True)

    class Meta:
        unique_together = ("room", "user")
        verbose_name = _("Участник комнаты")
        verbose_name_plural = _("Участники комнат")

    def __str__(self) -> str:
        return f"{self.user} @ {self.room}"


class ChatMessage(Create):
    room = models.ForeignKey(
        ChatRoom,
        verbose_name=_("Комната"),
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        User,
        verbose_name=_("Отправитель"),
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    text = models.TextField(_("Текст"))

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        ordering = ["created_at"]
        verbose_name = _("Сообщение чата")
        verbose_name_plural = _("Сообщения чата")

    def __str__(self) -> str:
        return f"{self.sender}: {self.text[:50]}"
