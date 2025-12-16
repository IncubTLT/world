from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import GeoCoverage, GeoCoverageBinding, PlaceType


class PlaceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaceType
        fields = [
            "id",
            "code",
            "name",
            "description",
            "radius_meters_default",
            "is_active",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")


class GeoCoverageSerializer(serializers.ModelSerializer):
    place_type_detail = PlaceTypeSerializer(
        source="place_type",
        read_only=True,
        help_text=_("Тип местности с радиусом по умолчанию."),
    )
    place_type = serializers.PrimaryKeyRelatedField(
        queryset=PlaceType.objects.filter(is_active=True),
        help_text=_("Тип местности из справочника."),
    )

    class Meta:
        model = GeoCoverage
        fields = [
            "id",
            "name",
            "latitude",
            "longitude",
            "radius_meters",
            "place_type",
            "place_type_detail",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "place_type_detail")


class GeoCoverageBindingReadSerializer(serializers.ModelSerializer):
    """
    Выводит привязку с краткой информацией о цели.
    """

    target_app_label = serializers.SerializerMethodField()
    target_model = serializers.SerializerMethodField()
    coverage = GeoCoverageSerializer(read_only=True)

    class Meta:
        model = GeoCoverageBinding
        fields = [
            "id",
            "coverage",
            "target_app_label",
            "target_model",
            "object_id",
            "created_at",
        ]
        read_only_fields = fields

    def get_target_app_label(self, obj: GeoCoverageBinding) -> str:
        return obj.content_type.app_label

    def get_target_model(self, obj: GeoCoverageBinding) -> str:
        return obj.content_type.model


class GeoCoverageBindingCreateSerializer(serializers.ModelSerializer):
    """
    Создание привязки точки покрытия к произвольной модели.
    """

    target_app_label = serializers.CharField(
        help_text=_("app_label модели, к которой прикрепляем точку покрытия."),
    )
    target_model = serializers.CharField(
        help_text=_("model_name модели, к которой прикрепляем точку покрытия."),
    )
    target_object_id = serializers.IntegerField(
        help_text=_("ID объекта, к которому прикрепляем точку покрытия."),
    )

    class Meta:
        model = GeoCoverageBinding
        fields = [
            "id",
            "coverage",
            "target_app_label",
            "target_model",
            "target_object_id",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)

        app_label = attrs.pop("target_app_label", None)
        model = attrs.pop("target_model", None)
        obj_id = attrs.pop("target_object_id", None)

        if not all([app_label, model, obj_id]):
            raise serializers.ValidationError(
                _(
                    "Нужно указать target_app_label, target_model и target_object_id "
                    "для создания привязки."
                )
            )

        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist as exc:
            raise serializers.ValidationError(
                _("Неизвестная модель: %(app)s.%(model)s") % {
                    "app": app_label,
                    "model": model,
                }
            ) from exc

        model_cls = ct.model_class()
        if model_cls is None:
            raise serializers.ValidationError(_("Указанная модель недоступна."))

        if not model_cls.objects.filter(pk=obj_id).exists():
            raise serializers.ValidationError(
                _("Объект %(model)s с ID %(id)s не найден.") % {
                    "model": model,
                    "id": obj_id,
                }
            )

        attrs["content_type"] = ct
        attrs["object_id"] = obj_id
        return attrs


class GeoCoverageDetailSerializer(GeoCoverageSerializer):
    bindings = GeoCoverageBindingReadSerializer(
        source="links",
        many=True,
        read_only=True,
    )

    class Meta(GeoCoverageSerializer.Meta):
        fields = GeoCoverageSerializer.Meta.fields + ["bindings"]
