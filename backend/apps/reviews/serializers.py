from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.filehub.serializers import MediaAttachmentSerializer
from apps.filehub.models import MediaAttachment
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    media = MediaAttachmentSerializer(
        source="media_attachments",
        many=True,
        read_only=True,
        help_text=_("Привязанные медиа через filehub."),
    )
    media_attachment_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text=_("Список ID MediaAttachment для привязки к отзыву (1–3 шт.)."),
    )
    author = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "author",
            "place",
            "rating",
            "text",
            "is_hidden",
            "media_attachment_ids",
            "media",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "author", "media", "created_at", "updated_at")

    def validate_media_attachment_ids(self, value):
        if not value:
            return []
        unique_ids = list(dict.fromkeys(value))
        if len(unique_ids) > 3:
            raise serializers.ValidationError(_("Можно прикрепить не более 3 медиафайлов к отзыву."))
        # Проверяем существование
        existing = set(
            MediaAttachment.objects.filter(id__in=unique_ids).values_list("id", flat=True)
        )
        missing = set(unique_ids) - existing
        if missing:
            raise serializers.ValidationError(
                _("Медиафайлы с ID %(ids)s не найдены.") % {"ids": ", ".join(map(str, missing))}
            )
        return unique_ids

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        role = getattr(user, "role", None) if user and user.is_authenticated else None
        is_mod = bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or role in ("admin", "moderator")))

        if not is_mod and "is_hidden" in attrs:
            # обычные пользователи не могут скрывать отзывы
            attrs.pop("is_hidden", None)
        return attrs

    def _sync_attachments(self, review: Review, attachment_ids: list[int]) -> None:
        ct = ContentType.objects.get_for_model(review)
        qs = MediaAttachment.objects.filter(content_type=ct, object_id=review.id)
        if attachment_ids is not None:
            qs.exclude(id__in=attachment_ids).delete()
        if not attachment_ids:
            return
        # Привяжем указанные ID к отзыву
        MediaAttachment.objects.filter(id__in=attachment_ids).update(
            content_type=ct,
            object_id=review.id,
        )

    def create(self, validated_data):
        attachment_ids = validated_data.pop("media_attachment_ids", [])
        review = super().create(validated_data)
        if attachment_ids:
            self._sync_attachments(review, attachment_ids)
        return review

    def update(self, instance, validated_data):
        attachment_ids = validated_data.pop("media_attachment_ids", None)
        review = super().update(instance, validated_data)
        if attachment_ids is not None:
            self._sync_attachments(review, attachment_ids)
        return review
