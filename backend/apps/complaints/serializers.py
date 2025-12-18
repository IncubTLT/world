from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import Complaint


class ComplaintSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    target_app_label = serializers.CharField(write_only=True, help_text=_("app_label объекта жалобы"))
    target_model = serializers.CharField(write_only=True, help_text=_("model_name объекта жалобы"))
    target_object_id = serializers.IntegerField(write_only=True, help_text=_("ID объекта жалобы"))

    class Meta:
        model = Complaint
        fields = [
            "id",
            "author",
            "target_app_label",
            "target_model",
            "target_object_id",
            "reason",
            "status",
            "moderator_comment",
            "snapshot",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "author",
            "snapshot",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # При обновлении не требуем target_* полей
        if self.instance:
            return attrs

        app_label = attrs.pop("target_app_label", None)
        model = attrs.pop("target_model", None)
        obj_id = attrs.pop("target_object_id", None)

        if not all([app_label, model, obj_id]):
            raise serializers.ValidationError(_("Необходимо указать target_app_label, target_model и target_object_id"))

        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist as exc:
            raise serializers.ValidationError(_("Модель не найдена: %(app)s.%(model)s") % {"app": app_label, "model": model}) from exc

        model_cls = ct.model_class()
        if model_cls is None:
            raise serializers.ValidationError(_("Указанная модель недоступна."))

        obj = model_cls.objects.filter(pk=obj_id).first()
        if obj is None:
            raise serializers.ValidationError(_("Объект с ID %(id)s не найден.") % {"id": obj_id})

        # сохраняем контент-тайп и object_id, а также опционально снэпшот
        attrs["content_type"] = ct
        attrs["object_id"] = obj_id
        attrs["snapshot"] = self._build_snapshot(obj, ct)
        return attrs

    def _build_snapshot(self, obj, ct: ContentType):
        # Краткая сводка для UI и модерации
        label = getattr(obj, "name", None) or getattr(obj, "title", None) or str(obj)
        return {
            "app_label": ct.app_label,
            "model": ct.model,
            "object_id": obj.pk,
            "label": label,
        }
