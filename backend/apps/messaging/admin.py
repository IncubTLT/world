from django.contrib import admin

from .models import ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_global", "created_at")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("participants",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "recipient", "room", "status", "sent_at")
    list_filter = ("status", "sent_at", "room")
    search_fields = ("body", "sender__email", "recipient__email")
