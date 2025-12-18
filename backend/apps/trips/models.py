from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from treebeard.mp_tree import MP_Node

from apps.geohub.models import GeoCoverable
from apps.places.models import Place
from apps.utils.models import CreateUpdater


class Trip(CreateUpdater):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trips",
        verbose_name=_("Владелец"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Название"))
    short_description = models.CharField(
        max_length=280,
        blank=True,
        verbose_name=_("Краткое описание"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Описание"),
    )
    is_public = models.BooleanField(
        default=True,
        verbose_name=_("Публичный"),
        help_text=_("Доступен другим пользователям."),
    )
    source_trip = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="forks",
        verbose_name=_("Исходный маршрут"),
        help_text=_("Для копий 'Сохранить себе' сохраняем ссылку на оригинал."),
    )
    is_hidden = models.BooleanField(
        default=False,
        verbose_name=_("Скрыт"),
        help_text=_("Можно скрыть без удаления (модерация)."),
    )

    class Meta:
        verbose_name = _("Маршрут")
        verbose_name_plural = _("Маршруты")
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return self.title


class TripPoint(GeoCoverable, MP_Node):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="points",
        verbose_name=_("Маршрут"),
    )
    note = models.CharField(
        max_length=512,
        blank=True,
        verbose_name=_("Заметка"),
    )
    place = models.ForeignKey(
        Place,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="trip_points",
        verbose_name=_("Место"),
        help_text=_("Связь с Place, если точка основана на существующем месте."),
    )

    class Meta:
        verbose_name = _("Точка маршрута")
        verbose_name_plural = _("Точки маршрута")
        ordering = ("path",)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"{self.trip.title} [{self.path}]"
