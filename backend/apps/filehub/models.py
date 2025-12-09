import uuid

from apps.utils.models import Create, CreateUpdater
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class MediaErrorCode(models.TextChoices):
    NONE = "", _("Нет ошибки")

    FORBIDDEN_EXTENSION = "forbidden_extension", _("Запрещённое расширение файла")
    BAD_EXTENSION = "bad_extension", _("Недопустимое расширение файла")
    BAD_MIME = "bad_mime", _("Недопустимый MIME-тип файла")
    TOO_LARGE = "too_large", _("Слишком большой файл")

    INFECTED = "infected", _("Файл заражён (антивирус)")
    CORRUPTED = "corrupted", _("Файл повреждён или не распознан")
    PROCESSING_ERROR = "processing_error", _("Внутренняя ошибка обработки файла")


class Status(models.TextChoices):
    PENDING = "pending", _("Ожидает загрузки")
    UPLOADED = "uploaded", _("Загружен в хранилище")
    PROCESSING = "processing", _("Обрабатывается")
    READY = "ready", _("Готов к использованию")
    FAILED = "failed", _("Ошибка")


class MediaFile(CreateUpdater):
    """
    Базовая сущность любого файла: фото, видео, документ и т.д.
    Хранит ключ (путь) файла в хранилище MediaStorage и метаданные.
    """

    class FileType(models.TextChoices):
        IMAGE = "image", _("Изображение")
        VIDEO = "video", _("Видео")
        DOCUMENT = "document", _("Документ")
        AUDIO = "audio", _("Аудио")
        OTHER = "other", _("Другое")

    class Visibility(models.TextChoices):
        PRIVATE = "private", _("Только владелец")
        AUTH = "auth", _("Все авторизованные пользователи")
        PUBLIC = "public", _("Доступен всем")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID файла"),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_files",
        verbose_name=_("Владелец файла"),
        help_text=_("Пользователь, загрузивший файл. Может быть пустым для системных файлов."),
    )

    key = models.CharField(
        max_length=1024,
        db_index=True,
        verbose_name=_("Путь в хранилище"),
        help_text=_("Ключ (путь) к файлу в бакете MediaStorage."),
    )

    original_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Исходное имя файла"),
        help_text=_("Имя файла при загрузке пользователем."),
    )

    file_type = models.CharField(
        max_length=16,
        choices=FileType.choices,
        default=FileType.OTHER,
        verbose_name=_("Тип файла"),
        help_text=_("Логический тип файла: изображение, видео, документ и т.д."),
        db_index=True,
    )

    content_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("MIME-тип"),
        help_text=_("MIME-тип файла (например, image/webp, application/pdf)."),
    )

    extension = models.CharField(
        max_length=16,
        blank=True,
        verbose_name=_("Расширение"),
        help_text=_("Расширение файла без точки, например: jpg, webp, pdf."),
    )

    size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Размер файла, байт"),
    )

    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
        verbose_name=_("Уровень доступа"),
        help_text=_("Кто может обращаться к файлу."),
        db_index=True,
    )

    checksum = models.CharField(
        max_length=128,
        blank=True,
        verbose_name=_("Хэш файла"),
        help_text=_("Например, SHA256 для проверки целостности и дедупликации."),
    )

    meta = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Дополнительные метаданные"),
        help_text=_("Произвольные служебные данные о файле (EXIF, длительность и т.п.)."),
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Статус файла"),
        db_index=True,
    )

    error_code = models.CharField(
        max_length=64,
        choices=MediaErrorCode.choices,
        blank=True,
        default=MediaErrorCode.NONE,
        verbose_name=_("Код ошибки"),
        help_text=_("Машинный код ошибки валидации или обработки файла."),
    )

    error_detail = models.TextField(
        blank=True,
        verbose_name=_("Описание ошибки"),
        help_text=_("Человекочитаемое описание ошибки (для логов и отладки)."),
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = _("Медиа-файл")
        verbose_name_plural = _("Медиа-файлы")
        indexes = [
            models.Index(fields=["owner", "file_type"], name="mediafile_owner_type_idx"),
            models.Index(fields=["key"], name="mediafile_key_idx"),
            models.Index(fields=["status"], name="mediafile_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.file_type}::{self.key}"

    @property
    def is_ready(self) -> bool:
        """
        Обратная совместимость: раньше было булево поле.
        Теперь считаем готовым, если статус READY.
        """
        return self.status == self.Status.READY  # pyright: ignore[reportAttributeAccessIssue]


class MediaFileVariant(Create):
    """
    Конкретный вариант файла (thumb, webp, превью и т.п.), привязанный к MediaFile.
    Физически также хранится в MediaStorage, ключ относительный к общему бакету.
    """

    class Kind(models.TextChoices):
        ORIGINAL = "original", _("Оригинал")
        WEBP = "webp", _("WebP-версия")
        THUMB_LARGE = "thumb_large", _("Крупный превью (800x800)")
        THUMB_SMALL = "thumb_small", _("Малый превью (300x300)")
        PREVIEW_BASE64 = "preview_base64", _("Мини-превью в Base64")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID варианта"),
    )

    media_file = models.ForeignKey(
        MediaFile,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name=_("Исходный файл"),
    )

    kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        verbose_name=_("Тип варианта"),
    )

    key = models.CharField(
        max_length=1024,
        db_index=True,
        verbose_name=_("Путь варианта в хранилище"),
        help_text=_("Ключ (путь) варианта файла в бакете MediaStorage."),
    )

    width = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Ширина, px"),
    )

    height = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Высота, px"),
    )

    size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Размер варианта, байт"),
    )

    content_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("MIME-тип варианта"),
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Статус обработки"),
        db_index=True,
    )

    error_code = models.CharField(
        max_length=64,
        choices=MediaErrorCode.choices,
        blank=True,
        default=MediaErrorCode.NONE,
        verbose_name=_("Код ошибки"),
    )

    error_message = models.TextField(
        blank=True,
        verbose_name=_("Сообщение об ошибке"),
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = _("Вариант медиа-файла")
        verbose_name_plural = _("Варианты медиа-файлов")
        unique_together = ("media_file", "kind")
        indexes = [
            models.Index(fields=["media_file", "kind"], name="media_variant_media_kind_idx"),
            models.Index(fields=["key"], name="media_variant_key_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.media_file_id}::{self.kind}"  # pyright: ignore[reportAttributeAccessIssue]


class MediaAttachment(Create):
    """
    Универсальная привязка медиа-файла к любой модели Джанги
    через GenericForeignKey.
    """

    class Role(models.TextChoices):
        MAIN = "main", _("Главное медиа")
        GALLERY = "gallery", _("Галерея")
        DOCUMENT = "document", _("Документ")
        AVATAR = "avatar", _("Аватар")
        OTHER = "other", _("Другое")

    id = models.BigAutoField(
        primary_key=True,
        verbose_name=_("ID привязки"),
    )

    # Generic FK
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Тип связанной модели"),
    )
    # Лучше PositiveBigIntegerField, если в проекте везде BigAutoField
    object_id = models.PositiveBigIntegerField(
        verbose_name=_("ID связанного объекта"),
    )
    content_object = GenericForeignKey("content_type", "object_id")

    media_file = models.ForeignKey(
        MediaFile,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("Медиа-файл"),
    )

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.OTHER,
        verbose_name=_("Роль медиа"),
        help_text=_("Назначение файла: главное фото, документ, аватар и т.д."),
        db_index=True,
    )

    priority = models.PositiveIntegerField(
        default=100,
        verbose_name=_("Приоритет"),
        help_text=_("Чем меньше число, тем выше приоритет отображения."),
    )

    is_primary = models.BooleanField(
        default=False,
        verbose_name=_("Главный файл в роли"),
        help_text=_("Если отмечен, считается главным в рамках данной роли и объекта."),
    )

    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Заголовок"),
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Описание"),
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = _("Привязка медиа-файла")
        verbose_name_plural = _("Привязки медиа-файлов")
        ordering = ["priority", "-created_at"]
        unique_together = ("content_type", "object_id", "media_file", "role")
        constraints = [
            # Не более одного primary для пары (объект, роль)
            models.UniqueConstraint(
                fields=["content_type", "object_id", "role"],
                condition=Q(is_primary=True),
                name="uniq_primary_media_per_object_and_role",
            ),
        ]
        indexes = [
            models.Index(
                fields=["content_type", "object_id"],
                name="media_attach_ct_obj_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.content_type_id}:{self.object_id} -> {self.media_file_id} ({self.role})"  # pyright: ignore[reportAttributeAccessIssue]
