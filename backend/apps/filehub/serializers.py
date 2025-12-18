from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import MediaFile, MediaAttachment
from .validators import validate_filename_and_type, validate_size_limit


class UploadInitFileSerializer(serializers.Serializer):
    """
    Описание одного файла, который клиент собирается загрузить.
    Здесь уже проверяем, что файл по имени/типу не выглядит подозрительным.
    """

    original_name = serializers.CharField(
        max_length=255,
        help_text=_("Имя файла на стороне клиента."),
    )
    file_type = serializers.ChoiceField(
        choices=MediaFile.FileType.choices,
        help_text=_("Тип файла (логический): изображение, видео, документ и т.д."),
    )
    content_type = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text=_("MIME-тип файла, если известен."),
    )
    visibility = serializers.ChoiceField(
        choices=MediaFile.Visibility.choices,
        required=False,
        default=MediaFile.Visibility.PRIVATE,
        help_text=_("Желаемый уровень доступа к файлу."),
    )

    # Привязка к объекту (опционально)
    target_app_label = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("app_label модели, к которой привязывается медиа."),
    )
    target_model = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("model_name модели, к которой привязывается медиа."),
    )
    target_object_id = serializers.IntegerField(
        required=False,
        help_text=_("ID объекта, к которому привязывается медиа."),
    )

    role = serializers.ChoiceField(
        choices=MediaAttachment.Role.choices,
        required=False,
        default=MediaAttachment.Role.OTHER,
        help_text=_("Роль медиа для указанного объекта."),
    )
    priority = serializers.IntegerField(
        required=False,
        help_text=_("Приоритет отображения медиа."),
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)

        original_name = attrs["original_name"]
        file_type = attrs["file_type"]
        content_type = attrs.get("content_type") or ""

        # 1) Проверяем «опасность» по имени и заявленному типу
        validate_filename_and_type(
            original_name=original_name,
            file_type=file_type,
            content_type=content_type,
        )

        # 2) Проверяем связку target_app_label/target_model/target_object_id
        app_label = attrs.get("target_app_label")
        model = attrs.get("target_model")
        obj_id = attrs.get("target_object_id")

        if any([app_label, model, obj_id]) and not all([app_label, model, obj_id]):
            raise serializers.ValidationError(
                _(
                    "Для привязки к объекту нужно указать target_app_label, "
                    "target_model и target_object_id."
                )
            )

        if app_label and model:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model)
            except ContentType.DoesNotExist:
                msg = _("Указанный тип модели не найден: %(app_label)s.%(model)s") % {
                    "app_label": app_label,
                    "model": model,
                }
                raise serializers.ValidationError(msg)
            attrs["target_content_type"] = ct

        return attrs


class UploadInitFileResultSerializer(serializers.Serializer):
    """
    Описание одного файла в ответе upload-init.
    """
    media_file_id = serializers.UUIDField(
        help_text=_("ID созданного медиа-файла в системе."),
    )
    key = serializers.CharField(
        help_text=_("Ключ (путь) файла в хранилище."),
    )
    visibility = serializers.ChoiceField(
        choices=MediaFile.Visibility.choices,
        help_text=_("Уровень доступа к файлу."),
    )

    upload = serializers.DictField(
        help_text=_(
            "Данные presigned POST для прямой загрузки в S3/MinIO."
        )
    )


class UploadInitResponseSerializer(serializers.Serializer):
    """
    Ответ upload-init: набор presigned-форм для загрузки.
    """
    files = UploadInitFileResultSerializer(
        many=True,
        help_text=_("Список файлов с данными для загрузки и ID в системе."),
    )


class UploadInitSerializer(serializers.Serializer):
    """
    Инициализация пачки загрузок.
    """
    files = UploadInitFileSerializer(
        many=True,
        help_text=_("Список файлов, которые клиент планирует загрузить."),
    )


class MediaAttachmentSerializer(serializers.ModelSerializer):
    """
    Read-only представление привязки медиа к объекту.
    """

    media_file = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = MediaAttachment
        fields = [
            "id",
            "media_file",
            "role",
            "priority",
            "is_primary",
            "title",
            "description",
            "created_at",
        ]
        read_only_fields = fields


class UploadCompleteSerializer(serializers.Serializer):
    """
    Подтверждение того, что файл залит в S3 и с ним можно работать дальше.
    """
    media_file_id = serializers.UUIDField(
        help_text=_("ID медиа-файла, для которого завершается загрузка."),
    )
    size_bytes = serializers.IntegerField(
        required=False,
        help_text=_("Фактический размер файла в байтах."),
    )
    checksum = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("Хэш содержимого файла (например, SHA256)."),
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)

        size_bytes = attrs.get("size_bytes")
        media_file_id = attrs.get("media_file_id")

        if size_bytes is not None and media_file_id:
            # нам нужен file_type, чтобы понимать лимит
            try:
                media = MediaFile.objects.only("file_type").get(id=media_file_id)
            except MediaFile.DoesNotExist:
                # это уже отловится во вьюхе, можно не рушить здесь
                return attrs

            validate_size_limit(size_bytes, file_type=media.file_type)

        return attrs


class MediaFileSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для вывода информации о медиа-файле.
    Используется в списках и деталях.
    """

    class Meta:
        model = MediaFile
        fields = [
            "id",
            "owner",
            "key",
            "original_name",
            "file_type",
            "content_type",
            "extension",
            "size_bytes",
            "visibility",
            "checksum",
            "meta",
            "status",
            "error_code",
            "error_detail",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner",
            "key",
            "checksum",
            "status",
            "error_code",
            "error_detail",
            "created_at",
            "updated_at",
        ]
