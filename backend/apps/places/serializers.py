from django.contrib.contenttypes.models import ContentType
from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.filehub.models import MediaAttachment
from apps.geohub.models import GeoCoverage, GeoCoverageBinding, PlaceType
from apps.geohub.serializers import (
    GeoCoverageBindingReadSerializer,
    GeoCoverageSerializer,
    PlaceTypeSerializer,
)

from .models import Place


class PlaceMediaAttachmentSerializer(serializers.ModelSerializer):
    media_file_id = serializers.UUIDField(read_only=True, help_text=_("ID медиа-файла в filehub."))

    class Meta:
        model = MediaAttachment
        fields = [
            "id",
            "media_file_id",
            "role",
            "priority",
            "is_primary",
            "title",
            "description",
            "created_at",
        ]
        read_only_fields = fields


class PlaceSerializer(serializers.ModelSerializer):
    coverages = serializers.SerializerMethodField(read_only=True, help_text=_("Привязанные точки покрытия."))
    coverage_ids = serializers.PrimaryKeyRelatedField(
        queryset=GeoCoverage.objects.all(),
        many=True,
        required=False,
        write_only=True,
        help_text=_("Список ID точек покрытия для привязки."),
    )
    media = PlaceMediaAttachmentSerializer(
        source="media_attachments",
        many=True,
        read_only=True,
        help_text=_("Привязанные медиа-файлы (создаются через filehub)."),
    )
    place_type_detail = PlaceTypeSerializer(
        source="place_type",
        read_only=True,
        help_text=_("Детали типа места."),
    )
    place_type = serializers.PrimaryKeyRelatedField(
        queryset=PlaceType.objects.filter(is_active=True),
        allow_null=True,
        required=False,
        help_text=_("ID типа места из справочника."),
    )
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    rating_avg = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        read_only=True,
        allow_null=True,
        help_text=_("Средняя оценка по месту (только по не скрытым отзывам)."),
    )
    rating_count = serializers.IntegerField(
        read_only=True,
        help_text=_("Количество отзывов (не скрытых)."),
    )

    class Meta:
        model = Place
        fields = [
            "id",
            "name",
            "description",
            "place_type",
            "place_type_detail",
            "country",
            "region",
            "city",
            "is_active",
            "coverages",
            "coverage_ids",
            "media",
            "rating_avg",
            "rating_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "coverages",
            "media",
            "rating_avg",
            "rating_count",
            "created_by",
            "created_at",
            "updated_at",
        )

    @extend_schema_field(GeoCoverageBindingReadSerializer(many=True))
    def get_coverages(self, obj: Place) -> list[dict[str, Any]]:
        bindings = obj.geo_coverages.select_related("coverage", "content_type").all()
        result: list[dict] = []
        for b in bindings:
            if not b.coverage_id:
                continue
            coverage_obj = b.coverage if hasattr(b, "coverage") else None
            if coverage_obj is None or isinstance(coverage_obj, models.Manager):
                coverage_obj = GeoCoverage.objects.filter(id=b.coverage_id).first()
            if coverage_obj is None:
                continue
            result.append(
                {
                    "id": b.id,
                    "coverage": GeoCoverageSerializer(coverage_obj, context=self.context).data,
                    "target_app_label": b.content_type.app_label,
                    "target_model": b.content_type.model,
                    "object_id": b.object_id,
                    "created_at": b.created_at,
                }
            )
        return result

    def _sync_coverages(self, instance: Place, coverage_list: list[GeoCoverage]) -> None:
        ct = ContentType.objects.get_for_model(instance)
        GeoCoverageBinding.objects.filter(content_type=ct, object_id=instance.pk).delete()
        coverage_ids = [c.id if hasattr(c, "id") else c for c in coverage_list]
        bindings = [
            GeoCoverageBinding(
                coverage_id=coverage_id,
                content_type=ct,
                object_id=instance.pk,
            )
            for coverage_id in coverage_ids
        ]
        if bindings:
            GeoCoverageBinding.objects.bulk_create(bindings)

    def create(self, validated_data):
        coverage_ids = validated_data.pop("coverage_ids", [])
        place = super().create(validated_data)
        if coverage_ids:
            self._sync_coverages(place, coverage_ids)
        return place

    def update(self, instance, validated_data):
        coverage_ids = validated_data.pop("coverage_ids", None)
        place = super().update(instance, validated_data)
        if coverage_ids is not None:
            self._sync_coverages(place, coverage_ids)
        return place
