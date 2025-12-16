from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.utils.models import Create, CreateUpdater


class GeoCoverage(CreateUpdater):
    name = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name=_("Название точки"),
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
        verbose_name=_("Широта"),
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
        verbose_name=_("Долгота"),
    )
    radius_meters = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name=_("Радиус действия, м"),
        help_text=_("Используется для определения пересечений координат."),
    )
    place_type = models.ForeignKey(
        "geohub.PlaceType",
        on_delete=models.PROTECT,
        related_name="coverages",
        verbose_name=_("Тип местности"),
        help_text=_("Определяет радиус по умолчанию и тип среды (город, лес и т.д.)."),
    )
    bindings = GenericRelation(
        "geohub.GeoCoverageBinding",
        related_query_name="coverage",
        verbose_name=_("Привязки к объектам"),
    )

    def save(self, *args, **kwargs):
        if self.radius_meters is None:
            self.radius_meters = (
                self.place_type.radius_meters_default if self.place_type else 1000
            )
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Точка покрытия")
        verbose_name_plural = _("Точки покрытия")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["latitude", "longitude"])]

    def __str__(self):
        label = self.name or f"{self.latitude}, {self.longitude}"
        type_label = self.place_type.name if self.place_type_id else _("Без типа")
        return f"{label} ({type_label}, {self.radius_meters}m)"


class GeoCoverageBinding(Create):
    """
    Привязка точки покрытия к любому объекту через GenericRelation.
    """

    coverage = models.ForeignKey(
        GeoCoverage,
        on_delete=models.CASCADE,
        related_name="links",
        verbose_name=_("Точка покрытия"),
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Тип объекта"),
    )
    object_id = models.PositiveIntegerField(verbose_name=_("ID объекта"))
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = _("Привязка точки покрытия")
        verbose_name_plural = _("Привязки точек покрытия")
        constraints = [
            models.UniqueConstraint(
                fields=["coverage", "content_type", "object_id"],
                name="uq_geo_coverage_binding_target",
            )
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.coverage} -> {self.content_type}.{self.object_id}"


class GeoCoverable(models.Model):
    """
    Абстрактный миксин для моделей, которым нужны точки покрытия.
    """

    geo_coverages = GenericRelation(
        GeoCoverageBinding,
        related_query_name="geo_target",
        verbose_name=_("Точки покрытия"),
    )

    class Meta:
        abstract = True


class PlaceType(Create):
    """
    Тип места (пляж, город, достопримечательность и т.п.) для использования в местах.
    """

    code = models.SlugField(
        max_length=32,
        unique=True,
        verbose_name=_("Код"),
        help_text=_("Уникальный код типа, используется на фронтенде и при импорте."),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("Название"),
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Описание"),
    )
    radius_meters_default = models.PositiveIntegerField(
        default=1000,
        validators=[MinValueValidator(1)],
        verbose_name=_("Радиус по умолчанию, м"),
        help_text=_("Будет подставлен в точку покрытия, если не указан вручную."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Активен"),
        help_text=_("Неактивные типы скрываются из списка."),
    )

    class Meta:
        verbose_name = _("Тип места")
        verbose_name_plural = _("Типы мест")
        ordering = ("name",)

    def __str__(self):
        return self.name
