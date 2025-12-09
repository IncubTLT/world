import uuid
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.utils.text import slugify

from .models import MediaFile


def build_media_key(
    *,
    file_type: str,
    visibility: str,
    original_name: str | None = None,
    owner_id: int | None = None,
    target_ct: ContentType | None = None,
    target_object_id: int | None = None,
) -> str:
    """
    Строит ключ (path) внутри MEDIA_BUCKET для MediaStorage.

    Пример результата:
    images/public/products/product/1234/2025/12/09/uuid.webp
    docs/private/users/user/42/2025/12/09/uuid.pdf
    """

    # Базовая папка по типу файла
    base_folder = {
        MediaFile.FileType.IMAGE: "images",
        MediaFile.FileType.VIDEO: "videos",
        MediaFile.FileType.DOCUMENT: "docs",
        MediaFile.FileType.AUDIO: "audio",
    }.get(file_type, "files")  # pyright: ignore[reportCallIssue, reportArgumentType]

    # public/private/auth
    visibility_folder = visibility or MediaFile.Visibility.PRIVATE

    # Привязка к модели (если есть)
    app_folder = "unbound"
    model_folder = "unbound"
    object_folder = "noobj"

    if target_ct and target_object_id:
        app_folder = slugify(target_ct.app_label) or target_ct.app_label
        model_folder = slugify(target_ct.model) or target_ct.model
        object_folder = str(target_object_id)

    # Владелец (не обязательно)
    owner_folder = f"user_{owner_id}" if owner_id else "anon"

    # Дата, чтобы не сыпать всё в одну папку
    today = datetime.utcnow()
    date_path = f"{today.year}/{today.month:02d}/{today.day:02d}"

    # Расширение можно выдрать из original_name (если есть)
    ext = ""
    if original_name and "." in original_name:
        ext = original_name.rsplit(".", 1)[-1].lower()
    if not ext:
        ext = "bin"

    file_uuid = uuid.uuid4()

    # Итоговый ключ
    key = (
        f"{base_folder}/"
        f"{visibility_folder}/"
        f"{app_folder}/"
        f"{model_folder}/"
        f"{object_folder}/"
        f"{owner_folder}/"
        f"{date_path}/"
        f"{file_uuid}.{ext}"
    )

    return key
