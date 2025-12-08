from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


class PlaceType(models.TextChoices):
    BEACH = "beach", "Beach"
    CITY = "city", "City"
    SIGHT = "sight", "Sight"
    TREK = "trek", "Trek"
    PARK = "park", "Park"
    MUSEUM = "museum", "Museum"
    OTHER = "other", "Other"


class Place(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    place_type = models.CharField(max_length=20, choices=PlaceType.choices, default=PlaceType.OTHER)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    main_photo = models.ImageField(
        upload_to="places/main/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="places",
        help_text="Needed for moderation and ownership",
    )
    is_active = models.BooleanField(default=True)  # allows moderation hiding without deletion
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["country", "region", "city"]),
            models.Index(fields=["latitude", "longitude"]),
        ]
        ordering = ("name",)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return self.name


class PlaceMedia(models.Model):
    class MediaType(models.TextChoices):
        PHOTO = "photo", "Photo"
        VIDEO = "video", "Video"

    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="media"
    )
    media_type = models.CharField(
        max_length=10,
        choices=MediaType.choices,
        default=MediaType.PHOTO
    )
    file = models.FileField(
        upload_to="places/extra/",
        validators=[FileExtensionValidator(
            ["jpg", "jpeg", "png", "webp", "mp4", "mov"]
            )],
    )
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "id")

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"{self.place.name} media #{self.pk}"
