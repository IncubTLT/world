from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.filehub.models import MediaAttachment
from apps.geohub.models import GeoCoverable, PlaceType
from apps.utils.models import CreateUpdater


class Place(GeoCoverable, CreateUpdater):
    name = models.CharField(
        max_length=255,
        verbose_name=_("Название"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Описание"),
    )
    place_type = models.ForeignKey(
        PlaceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="places",
        verbose_name=_("Тип места"),
        help_text=_("Выбирается из справочника типов мест."),
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Страна"),
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Регион"),
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Город"),
    )
    media_attachments = GenericRelation(
        MediaAttachment,
        related_query_name="place",
        verbose_name=_("Медиа-файлы"),
        help_text=_("Привязанные медиа-файлы через filehub."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Активно"),
        help_text=_("Можно скрыть место без удаления."),
    )

    class Meta:
        verbose_name = _("Место")
        verbose_name_plural = _("Места")
        indexes = [
            models.Index(fields=["country", "region", "city"]),
            models.Index(fields=["place_type", "is_active"]),
        ]
        ordering = ("name",)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return self.name
