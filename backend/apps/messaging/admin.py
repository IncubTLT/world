from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import ChatRoom, ChatRoomParticipant, ChatMessage


class ChatRoomParticipantInline(admin.TabularInline):
    """
    Участники комнаты — редактируются прямо из комнаты.
    """
    model = ChatRoomParticipant
    extra = 1
    autocomplete_fields = ["user"]
    fields = ("user", "is_admin", "joined_at")
    readonly_fields = ("joined_at",)
    show_change_link = True


class ChatMessageInline(admin.TabularInline):
    """
    Сообщения комнаты — только для чтения, чтобы видеть контекст.
    """
    model = ChatMessage
    extra = 0
    fields = ("created_at", "sender", "short_text")
    readonly_fields = ("created_at", "sender", "short_text")
    can_delete = False
    ordering = ("created_at",)

    @admin.display(description=_("Текст"))
    def short_text(self, obj: ChatMessage) -> str:
        return (obj.text[:80] + "…") if len(obj.text) > 80 else obj.text


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """
    Удобное управление комнатами:
    - фильтр по типу,
    - поиск по названию, владельцу и участникам,
    - инлайны: участники + сообщения.
    """
    list_display = (
        "id",
        "type",
        "name",
        "owner",
        "participants_count",
        "created_at",
        "updated_at",
    )
    list_filter = ("type", "owner")
    search_fields = (
        "id",
        "name",
        "owner__email",
        "owner__display_name",
        "participants__email",
        "participants__display_name",
    )
    autocomplete_fields = ("owner",)
    inlines = (ChatRoomParticipantInline, ChatMessageInline)
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)

    @admin.display(description=_("Кол-во участников"))
    def participants_count(self, obj: ChatRoom) -> int:
        return obj.participants.count()


@admin.register(ChatRoomParticipant)
class ChatRoomParticipantAdmin(admin.ModelAdmin):
    """
    Отдельный просмотр/редактирование участия пользователя в комнатах.
    Удобно, если нужно найти все комнаты конкретного пользователя.
    """
    list_display = ("room", "user", "is_admin", "joined_at")
    list_filter = ("is_admin",)
    search_fields = (
        "room__id",
        "room__name",
        "user__email",
        "user__display_name",
    )
    autocomplete_fields = ("room", "user")
    readonly_fields = ("joined_at",)
    ordering = ("-joined_at",)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """
    Админка для сообщений:
    - просмотр истории по комнате/пользователю,
    - поиск по тексту,
    - по умолчанию только чтение.
    """
    list_display = ("created_at", "room", "sender", "short_text")
    list_filter = ("room", "sender")
    search_fields = (
        "text",
        "room__id",
        "room__name",
        "sender__email",
        "sender__display_name",
    )
    autocomplete_fields = ("room", "sender")
    readonly_fields = ("created_at", "room", "sender", "text")
    ordering = ("-created_at",)

    @admin.display(description=_("Текст"))
    def short_text(self, obj: ChatMessage) -> str:
        return (obj.text[:80] + "…") if len(obj.text) > 80 else obj.text
