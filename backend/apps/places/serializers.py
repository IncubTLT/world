from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.filehub.models import MediaAttachment
from apps.geohub.models import GeoCoverage, GeoCoverageBinding, PlaceType
from apps.geohub.serializers import GeoCoverageBindingReadSerializer, PlaceTypeSerializer

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
    coverages = GeoCoverageBindingReadSerializer(
        source="geo_coverages",
        many=True,
        read_only=True,
        help_text=_("Привязанные точки покрытия."),
    )
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
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "coverages", "media", "created_by", "created_at", "updated_at")

    def _sync_coverages(self, instance: Place, coverage_list: list[GeoCoverage]) -> None:
        ct = ContentType.objects.get_for_model(instance)
        GeoCoverageBinding.objects.filter(content_type=ct, object_id=instance.pk).delete()
        bindings = [
            GeoCoverageBinding(
                coverage=coverage,
                content_type=ct,
                object_id=instance.pk,
            )
            for coverage in coverage_list
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
