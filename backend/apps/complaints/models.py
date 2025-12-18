from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.utils.models import CreateUpdater


class ComplaintStatus(models.TextChoices):
    OPEN = "open", _("Открыта")
    RESOLVED = "resolved", _("Решена")
    DISMISSED = "dismissed", _("Отклонена")


class Complaint(CreateUpdater):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="complaints",
        verbose_name=_("Автор жалобы"),
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Тип объекта"),
    )
    object_id = models.PositiveIntegerField(verbose_name=_("ID объекта"))
    content_object = GenericForeignKey("content_type", "object_id")

    reason = models.TextField(verbose_name=_("Причина/текст жалобы"))
    status = models.CharField(
        max_length=16,
        choices=ComplaintStatus.choices,
        default=ComplaintStatus.OPEN,
        verbose_name=_("Статус"),
    )
    moderator_comment = models.TextField(
        blank=True,
        verbose_name=_("Комментарий модератора"),
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Закрыта в"),
    )
    snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Снэпшот объекта"),
        help_text=_("Опционально: зафиксировать краткие данные о целевом объекте на момент жалобы."),
    )

    class Meta(CreateUpdater.Meta):
        verbose_name = _("Жалоба")
        verbose_name_plural = _("Жалобы")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"{self.author} -> {self.content_object} ({self.status})"
