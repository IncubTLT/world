from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class ComplaintStatus(models.TextChoices):
    OPEN = "open", "Open"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"


class Complaint(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=ComplaintStatus.choices, default=ComplaintStatus.OPEN)
    moderator_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return f"Complaint by {self.author} about {self.content_object}"
