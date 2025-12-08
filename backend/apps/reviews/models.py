from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models

from apps.places.models import Place


class Review(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField()
    is_hidden = models.BooleanField(default=False)  # admin/moderator can hide without deleting
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        unique_together = ("author", "place")  # keeps single active review per author/place

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"{self.place.name} ({self.rating}/5)"


class ReviewMedia(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="media")
    image = models.ImageField(
        upload_to="reviews/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
        help_text="Limit to 3 photos per review in forms/serializers",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"Review {self.review_id} image"
