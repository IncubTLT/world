from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import MediaErrorCode, MediaFile


# Разрешённые расширения по типу файла
ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    MediaFile.FileType.IMAGE: {".jpg", ".jpeg", ".png", ".webp"},
    MediaFile.FileType.VIDEO: {".mp4", ".mov", ".avi", ".mkv"},
    MediaFile.FileType.DOCUMENT: {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"},
    MediaFile.FileType.AUDIO: {".mp3", ".wav", ".ogg"},
    MediaFile.FileType.OTHER: set(),  # можно оставить пустым или разрешить что-то отдельно
}

# Жёсткий deny-list расширений (даже если кто-то попытается под видом DOCUMENT)
FORBIDDEN_EXTENSIONS: set[str] = {
    ".php",
    ".phtml",
    ".phar",
    ".cgi",
    ".pl",
    ".jsp",
    ".asp",
    ".aspx",
    ".js",
    ".mjs",
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".ps1",
    ".dll",
    ".so",
}


# Разрешённые префиксы MIME по типу файла
ALLOWED_MIME_PREFIXES: dict[str, Iterable[str]] = {
    MediaFile.FileType.IMAGE: ("image/",),
    MediaFile.FileType.VIDEO: ("video/",),
    MediaFile.FileType.DOCUMENT: (
        "application/pdf",
        "application/msword",
        "application/vnd.",
        "text/plain",
    ),
    MediaFile.FileType.AUDIO: ("audio/",),
    MediaFile.FileType.OTHER: (),
}


def validate_filename_and_type(
    *,
    original_name: str,
    file_type: str,
    content_type: str | None,
) -> None:
    """
    Базовая проверка по расширению и заявленному MIME.
    Делается до реальной загрузки файла.
    """
    content_type = (content_type or "").strip().lower()
    ext = Path(original_name).suffix.lower()

    # 1. Жёсткий deny-list
    if ext in FORBIDDEN_EXTENSIONS:
        msg = _("Файлы с расширением %(ext)s запрещены к загрузке.") % {"ext": ext}
        raise serializers.ValidationError(msg, code=MediaErrorCode.FORBIDDEN_EXTENSION)

    # 2. Разрешённые расширения по логическому типу
    allowed_exts = ALLOWED_EXTENSIONS.get(file_type) or set()
    if allowed_exts and ext not in allowed_exts:
        msg = _(
            "Файлы типа %(file_type)s могут иметь только следующие расширения: %(exts)s. "
            "Текущее расширение: %(ext)s."
        ) % {
            "file_type": file_type,
            "exts": ", ".join(sorted(allowed_exts)),
            "ext": ext or _("(отсутствует)"),
        }
        raise serializers.ValidationError(msg, code=MediaErrorCode.BAD_EXTENSION)

    # 3. Проверка заявленного MIME (если пришёл)
    if content_type:
        allowed_prefixes = ALLOWED_MIME_PREFIXES.get(file_type) or ()
        if allowed_prefixes:
            if not any(
                content_type == p or content_type.startswith(p) for p in allowed_prefixes
            ):
                msg = _(
                    "Указанный MIME-тип %(ct)s не соответствует ожидаемому для типа файла %(file_type)s."
                ) % {"ct": content_type, "file_type": file_type}
                raise serializers.ValidationError(msg, code=MediaErrorCode.BAD_MIME)


def validate_size_limit(size_bytes: int | None, *, file_type: str) -> None:
    """
    Проверка ограничения по размеру (делается после заливки, когда размер известен).
    Лимиты можно вынести в settings, чтобы легко крутить.
    """
    if size_bytes is None:
        return

    # Лимиты можно задать в settings, а здесь считать дефолты
    default_limits_mb = {
        MediaFile.FileType.IMAGE: 15,
        MediaFile.FileType.VIDEO: 500,
        MediaFile.FileType.DOCUMENT: 50,
        MediaFile.FileType.AUDIO: 100,
        MediaFile.FileType.OTHER: 50,
    }
    # Например, settings.FILEHUB_MAX_SIZE_OVERRIDES = {"image": 10, "video": 400}
    overrides: dict[str, int] = getattr(
        settings, "FILEHUB_MAX_SIZE_OVERRIDES", {}
    )

    limit_mb = overrides.get(file_type, default_limits_mb[file_type])  # pyright: ignore[reportArgumentType]
    limit_bytes = limit_mb * 1024 * 1024

    if size_bytes > limit_bytes:
        msg = _(
            "Файл слишком большой: %(size)d байт. Максимально допустимый размер для этого типа — %(limit)d МБ."
        ) % {"size": size_bytes, "limit": limit_mb}
        raise serializers.ValidationError(msg, code=MediaErrorCode.TOO_LARGE)
