from django.conf import settings
from django.db import models


class ChatRoom(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=120)
    is_global = models.BooleanField(default=False)  # single shared room for "общий" чат
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="chat_rooms",
        blank=True,
        help_text="Direct rooms can store participants for quick listing",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return self.title


class MessageStatus(models.TextChoices):
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    READ = "read", "Read"


class Message(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages",
        help_text="Nullable for direct 1:1 messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="received_messages",
    )
    body = models.TextField()
    status = models.CharField(
        max_length=12,
        choices=MessageStatus.choices,
        default=MessageStatus.SENT,
        help_text="Tracks sent/received/read without websockets",
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-sent_at",)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        recipient = self.recipient.email if self.recipient else (self.room or "?")
        return f"From {self.sender} to {recipient}"
