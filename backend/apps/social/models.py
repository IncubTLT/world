from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "target")

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"{self.follower} -> {self.target}"


class Activity(models.Model):
    class Verb(models.TextChoices):
        TRIP_CREATED = "trip_created", "Trip created"
        REVIEW_CREATED = "review_created", "Review created"
        FOLLOWED = "followed", "Followed"

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activities")
    verb = models.CharField(max_length=32, choices=Verb.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"{self.actor} {self.verb} {self.target}"
