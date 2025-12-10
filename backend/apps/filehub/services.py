import io
from typing import Tuple

from django.conf import settings
from PIL import Image as PIL_Image
from PIL import UnidentifiedImageError

from .models import MediaErrorCode, MediaFile, MediaFileVariant, Status


def _build_variant_key(media: MediaFile, suffix: str) -> str:
    base = media.key
    if "." in base:
        base = base.rsplit(".", 1)[0]
    return f"{base}/variants/{suffix}.webp"


async def _create_image_variant(
    *,
    client,
    media: MediaFile,
    base_img: PIL_Image.Image,
    kind: str,
    thumbnail_size: Tuple[int, int],
) -> MediaFileVariant:
    img = base_img.copy()
    img.thumbnail(thumbnail_size)

    bytes_io = io.BytesIO()
    img.save(bytes_io, format="WEBP")
    bytes_io.seek(0)

    key = _build_variant_key(media, suffix=kind)

    client.put_object(
        Bucket=settings.MEDIA_BUCKET_NAME,
        Key=key,
        Body=bytes_io.getvalue(),
        ContentType="image/webp",
    )

    variant, _ = await MediaFileVariant.objects.aupdate_or_create(
        media_file=media,
        kind=kind,
        defaults={
            "key": key,
            "status": Status.READY,
            "content_type": "image/webp",
            "size_bytes": len(bytes_io.getvalue()),
            "error_code": MediaErrorCode.NONE,
            "error_message": "",
        },
    )
    return variant


async def process_media_file_variants(media_file_id: str) -> None:
    media = await MediaFile.objects.aget(id=media_file_id)
    client = settings.S3_CLIENT

    # Если это не картинка — просто считаем файл готовым
    if media.file_type != MediaFile.FileType.IMAGE:
        media.status = Status.READY
        media.error_code = MediaErrorCode.NONE
        media.error_detail = ""
        await media.asave(update_fields=["status", "error_code", "error_detail"])
        return

    try:
        # Помечаем как "обрабатывается"
        media.status = Status.PROCESSING
        media.error_code = MediaErrorCode.NONE
        media.error_detail = ""
        await media.asave(update_fields=["status", "error_code", "error_detail"])

        # 1. Тянем картинку из S3
        obj = client.get_object(Bucket=settings.MEDIA_BUCKET_NAME, Key=media.key)
        content = obj["Body"].read()
        img = PIL_Image.open(io.BytesIO(content))

        variants_spec: list[tuple[str, Tuple[int, int]]] = [
            (MediaFileVariant.Kind.THUMB_LARGE, (800, 800)),
            (MediaFileVariant.Kind.THUMB_SMALL, (300, 300)),
        ]

        MediaFileVariant.objects.aget_or_create(
            media_file=media,
            kind=MediaFileVariant.Kind.ORIGINAL,
            defaults={
                "key": media.key,
                "status": Status.READY,
                "content_type": media.content_type or "image/*",
                "size_bytes": media.size_bytes,
                "error_code": MediaErrorCode.NONE,
                "error_message": "",
            },
        )

        for kind, size in variants_spec:
            await _create_image_variant(
                client=client,
                media=media,
                base_img=img,
                kind=kind,
                thumbnail_size=size,
            )

        media.status = Status.READY
        media.error_code = MediaErrorCode.NONE
        media.error_detail = ""
        await media.asave(update_fields=["status", "error_code", "error_detail"])

    except UnidentifiedImageError as e:
        # Файл не распознаётся как картинка
        msg = str(e)
        media.status = Status.FAILED
        media.error_code = MediaErrorCode.CORRUPTED
        media.error_detail = msg
        await media.asave(update_fields=["status", "error_code", "error_detail"])

        await MediaFileVariant.objects.filter(media_file=media).aupdate(
            status=Status.FAILED,
            error_code=MediaErrorCode.CORRUPTED,
            error_message=msg[:1000],
        )

    except Exception as e:
        # Любая другая ошибка обработки
        msg = str(e)
        media.status = Status.FAILED
        media.error_code = MediaErrorCode.PROCESSING_ERROR
        media.error_detail = msg
        await media.asave(update_fields=["status", "error_code", "error_detail"])

        await MediaFileVariant.objects.filter(media_file=media).aupdate(
            status=Status.FAILED,
            error_code=MediaErrorCode.PROCESSING_ERROR,
            error_message=msg[:1000],
        )
