from django.conf import settings
from django.db import models

from apps.places.models import Place


class Trip(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trips")
    title = models.CharField(max_length=255)
    short_description = models.CharField(max_length=280, blank=True)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)
    source_trip = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="forks",
        help_text="Keeps attribution for 'Save to myself' copies",
    )
    is_hidden = models.BooleanField(default=False)  # allows admin/moderation to hide without delete
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return self.title


class TripPoint(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="points")
    order = models.PositiveSmallIntegerField()  # rendering order in route
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    note = models.CharField(max_length=255, blank=True)
    place = models.ForeignKey(
        Place,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="trip_points",
        help_text="Optional link when point is based on an existing Place",
    )

    class Meta:
        ordering = ("order",)
        unique_together = ("trip", "order")

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"{self.trip.title} #{self.order}"
