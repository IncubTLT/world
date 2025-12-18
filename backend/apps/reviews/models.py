from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.filehub.models import MediaAttachment
from apps.places.models import Place
from apps.utils.models import CreateUpdater


class Review(CreateUpdater):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("Автор"),
    )
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("Место"),
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Оценка"),
    )
    text = models.TextField(verbose_name=_("Текст отзыва"))
    is_hidden = models.BooleanField(
        default=False,
        verbose_name=_("Скрыт"),
        help_text=_("Можно скрыть без удаления (модерация)."),
    )
    media_attachments = GenericRelation(
        MediaAttachment,
        related_query_name="review",
        verbose_name=_("Медиа-файлы"),
        help_text=_("Привязанные медиа через filehub."),
    )

    class Meta:
        verbose_name = _("Отзыв")
        verbose_name_plural = _("Отзывы")
        ordering = ("-created_at",)
        unique_together = ("author", "place")

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"{self.place.name} ({self.rating}/5)"
