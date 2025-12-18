from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.utils.models import Create


class Follow(Create):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
        verbose_name=_("Подписчик"),
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",
        verbose_name=_("Автор"),
    )

    class Meta:
        verbose_name = _("Подписка")
        verbose_name_plural = _("Подписки")
        unique_together = ("follower", "target")
        indexes = [
            models.Index(fields=["follower", "target"]),
            models.Index(fields=["target", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"{self.follower} -> {self.target}"


class Activity(Create):
    class Verb(models.TextChoices):
        TRIP_CREATED = "trip_created", _("Создан маршрут")
        REVIEW_CREATED = "review_created", _("Создан отзыв")
        MEDIA_ADDED = "media_added", _("Добавлено медиа")
        FOLLOWED = "followed", _("Подписался")

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name=_("Автор события"),
    )
    verb = models.CharField(max_length=32, choices=Verb.choices, verbose_name=_("Действие"))
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_("Тип объекта"))
    object_id = models.PositiveIntegerField(verbose_name=_("ID объекта"))
    target = GenericForeignKey("content_type", "object_id")
    payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Данные события"),
        help_text=_("Кешированный снэпшот: заголовок, короткое описание, ссылки."),
    )
    is_recommended = models.BooleanField(
        default=False,
        verbose_name=_("Рекомендовано"),
        help_text=_("Помечает событие как подобранное случайно/рекомендованное."),
    )

    class Meta:
        verbose_name = _("Событие")
        verbose_name_plural = _("События")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["is_recommended", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"{self.actor} {self.verb} {self.target}"
