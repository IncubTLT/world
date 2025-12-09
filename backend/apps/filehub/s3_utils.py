from typing import Any, Dict

from django.conf import settings

client = settings.S3_CLIENT


def generate_presigned_post(key: str, expires_in: int = 300) -> Dict[str, Any]:
    """
    Создаёт presigned POST для загрузки файла напрямую в бакет MEDIA_BUCKET_NAME.
    """
    return client.generate_presigned_post(
        Bucket=settings.MEDIA_BUCKET_NAME,
        Key=key,
        ExpiresIn=expires_in,
    )


def generate_presigned_put(key: str, content_type: str | None = None, expires_in: int = 3600) -> dict:
    params: dict = {
        "Bucket": settings.MEDIA_BUCKET_NAME,
        "Key": key,
    }
    if content_type:
        params["ContentType"] = content_type

    url = client.generate_presigned_url(
        ClientMethod="put_object",
        Params=params,
        ExpiresIn=expires_in,
    )
    return {
        "url": url,
        "method": "PUT",
        "headers": {
            **({"Content-Type": content_type} if content_type else {})
        },
    }
