from asgiref.sync import async_to_sync
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import (OpenApiExample, OpenApiResponse,
                                   extend_schema, extend_schema_view)
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MediaAttachment, MediaErrorCode, MediaFile, Status
from .permissions import MediaFilePermission
from .s3_utils import generate_presigned_put
from .serializers import (MediaFileSerializer, UploadCompleteSerializer,
                          UploadInitResponseSerializer, UploadInitSerializer)
from .tasks import process_media_file_variants_task
from .utils import build_media_key


@extend_schema(
    operation_id="filehub_upload_init",
    tags=["media"],
    summary=_("Инициализация загрузки файлов"),
    description=_(
        "Создаёт записи медиа-файлов и (опционально) привязки к объектам. "
        "Возвращает presigned POST формы для прямой загрузки файлов в S3/MinIO. "
        "Фактическая загрузка файла осуществляется клиентом непосредственно в хранилище."
    ),
    request=UploadInitSerializer,
    responses={
        201: OpenApiResponse(
            response=UploadInitResponseSerializer,
            description=_("Presigned данные для загрузки файлов успешно сгенерированы."),
        ),
        400: OpenApiResponse(
            description=_("Ошибка валидации входных данных (опасное расширение, MIME, неверная привязка к объекту и т.п.).")
        ),
        401: OpenApiResponse(description=_("Пользователь не авторизован.")),
    },
    examples=[
        OpenApiExample(
            name="Инициализация загрузки двух изображений",
            value={
                "files": [
                    {
                        "original_name": "avatar.png",
                        "file_type": "image",
                        "content_type": "image/png",
                        "visibility": "private",
                        "target_app_label": "users",
                        "target_model": "user",
                        "target_object_id": 42,
                        "role": "avatar",
                        "priority": 10,
                    },
                    {
                        "original_name": "product-photo.jpg",
                        "file_type": "image",
                        "content_type": "image/jpeg",
                        "visibility": "public",
                        "target_app_label": "catalog",
                        "target_model": "product",
                        "target_object_id": 1001,
                        "role": "gallery",
                        "priority": 100,
                    },
                ]
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Ответ upload-init",
            value={
                "files": [
                    {
                        "media_file_id": "4a9e15c4-8b3e-4f93-9dfb-2b4e235db1e9",
                        "key": "images/private/users/user/42/user_42/2025/12/09/xxx.png",
                        "visibility": "private",
                        "upload": {
                            "url": "https://minio.example.com/media-bucket",
                            "fields": {
                                "key": "images/private/users/user/42/user_42/2025/12/09/xxx.png",
                                "policy": "BASE64_POLICY",
                                "x-amz-algorithm": "AWS4-HMAC-SHA256",
                                "x-amz-credential": "ACCESS_KEY/...",
                                "x-amz-date": "20251209T120000Z",
                                "x-amz-signature": "SIGNATURE",
                            },
                        },
                    }
                ]
            },
            response_only=True,
        ),
    ],
)
class UploadInitView(APIView):
    """
    1) Создаёт записи MediaFile (и при необходимости MediaAttachment).
    2) Генерирует presigned POST-формы для загрузки в S3/MinIO.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UploadInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        results: list[dict] = []

        for item in serializer.validated_data["files"]:  # pyright: ignore[reportIndexIssue, reportOptionalSubscript]
            visibility = item.get("visibility") or MediaFile.Visibility.PRIVATE
            ct: ContentType | None = item.get("target_content_type")
            obj_id = item.get("target_object_id")

            key = build_media_key(
                file_type=item["file_type"],
                visibility=visibility,
                original_name=item["original_name"],
                owner_id=request.user.id,
                target_ct=ct,
                target_object_id=obj_id,
            )

            media = MediaFile.objects.create(
                owner=request.user,
                key=key,
                original_name=item["original_name"],
                file_type=item["file_type"],
                content_type=item.get("content_type") or "",
                visibility=visibility,
            )

            # При необходимости — сразу создаём привязку
            if ct and obj_id:
                MediaAttachment.objects.create(
                    content_type=ct,
                    object_id=obj_id,
                    media_file=media,
                    role=item.get("role") or MediaAttachment.Role.OTHER,
                    priority=item.get("priority") or 100,
                )

            presigned = generate_presigned_put(
                key,
                content_type=item.get("content_type") or None,
            )

            results.append(
                {
                    "media_file_id": str(media.id),
                    "key": key,
                    "visibility": visibility,
                    "upload": presigned,  # {url, method, headers}
                }
            )

        return Response({"files": results}, status=status.HTTP_201_CREATED)


@extend_schema(
    operation_id="filehub_upload_complete",
    tags=["media"],
    summary=_("Подтверждение завершения загрузки файла"),
    description=_(
        "Вызывается клиентом после успешной загрузки файла в S3/MinIO. "
        "Обновляет метаданные (размер, чек-сумма) и переводит файл в статус 'uploaded'. "
        "После этого запускается асинхронная обработка (создание превью, webp и т.п.)."
    ),
    request=UploadCompleteSerializer,
    responses={
        204: OpenApiResponse(description=_("Загрузка подтверждена, обработка запущена.")),
        400: OpenApiResponse(description=_("Ошибка валидации (например, превышен лимит размера файла).")),
        401: OpenApiResponse(description=_("Пользователь не авторизован.")),
        403: OpenApiResponse(description=_("Нет прав подтверждать загрузку этого файла.")),
        404: OpenApiResponse(description=_("Медиа-файл не найден.")),
    },
    examples=[
        OpenApiExample(
            name="Подтверждение загрузки",
            value={
                "media_file_id": "4a9e15c4-8b3e-4f93-9dfb-2b4e235db1e9",
                "size_bytes": 123456,
                "checksum": "e3b0c44298fc1c149afbf4c8996fb924..."
            },
            request_only=True,
        ),
    ],
)
class UploadCompleteView(APIView):
    """
    Клиент вызывает после успешной загрузки в S3.
    Обновляем метаданные и стартуем асинхронную обработку.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UploadCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        media_id = serializer.validated_data["media_file_id"]  # pyright: ignore[reportOptionalSubscript, reportIndexIssue]
        try:
            media = MediaFile.objects.get(id=media_id)
        except MediaFile.DoesNotExist:
            return Response(
                {"detail": _("Медиа-файл не найден.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if media.owner_id != request.user.id and not request.user.is_staff:  # pyright: ignore[reportAttributeAccessIssue]
            return Response(
                {"detail": _("Нет прав подтверждать загрузку этого файла.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        size_bytes = serializer.validated_data.get("size_bytes")  # type: ignore
        checksum = serializer.validated_data.get("checksum")  # type: ignore

        updated_fields: list[str] = []

        if size_bytes is not None:
            media.size_bytes = size_bytes
            updated_fields.append("size_bytes")

        if checksum:
            media.checksum = checksum
            updated_fields.append("checksum")

        # помечаем, что файл загружен и готов к обработке
        media.status = Status.UPLOADED
        media.error_code = MediaErrorCode.NONE
        media.error_detail = ""
        updated_fields.extend(["status", "error_code", "error_detail"])

        media.save(update_fields=list(set(updated_fields)))

        async_to_sync(process_media_file_variants_task.kiq)(str(media.id))

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        operation_id="filehub_mediafile_list",
        tags=["media"],
        summary=_("Список медиа-файлов"),
        description=_(
            "Возвращает список медиа-файлов, доступных текущему пользователю. "
            "Обычный пользователь видит свои файлы и публичные/доступные авторизованным "
            "файлы других пользователей. Администратор видит все файлы."
        ),
        responses={
            200: OpenApiResponse(
                response=MediaFileSerializer(many=True),
                description=_("Список медиа-файлов с информацией о статусе и ошибках."),
            ),
            401: OpenApiResponse(description=_("Пользователь не авторизован.")),
        },
    ),
    retrieve=extend_schema(
        operation_id="filehub_mediafile_retrieve",
        tags=["media"],
        summary=_("Детальная информация о медиа-файле"),
        description=_(
            "Возвращает полную информацию о медиа-файле (тип, ключ, статус, коды ошибок и т.п.), "
            "если у пользователя есть права на доступ к файлу."
        ),
        responses={
            200: OpenApiResponse(
                response=MediaFileSerializer,
                description=_("Детальная информация о медиа-файле."),
            ),
            401: OpenApiResponse(description=_("Пользователь не авторизован.")),
            403: OpenApiResponse(description=_("Нет прав доступа к этому медиа-файлу.")),
            404: OpenApiResponse(description=_("Медиа-файл не найден.")),
        },
    ),
)
class MediaFileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Базовое API для просмотра своих медиа-файлов.
    (Список/деталь, фильтрация можно будет добавить позже.)
    """

    serializer_class = MediaFileSerializer
    permission_classes = [IsAuthenticated, MediaFilePermission]

    def get_queryset(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        qs = MediaFile.objects.all()

        user = self.request.user
        if not user.is_authenticated:
            # На всякий случай — но сюда и так не попадём
            return qs.filter(visibility=MediaFile.Visibility.PUBLIC)

        if user.is_staff:  # pyright: ignore[reportAttributeAccessIssue]
            return qs  # админ видит всё

        # Обычный пользователь:
        # - свои файлы любого уровня доступа
        # - чужие только PUBLIC/AUTH
        return qs.filter(
            Q(visibility__in=[MediaFile.Visibility.PUBLIC, MediaFile.Visibility.AUTH])
            | Q(owner=user)
        )
