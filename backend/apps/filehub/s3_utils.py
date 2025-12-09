import boto3
from typing import Any, Dict

from django.conf import settings


def get_s3_client():
    """
    Возвращает S3-клиент.
    Настрой под свои ENV (endpoint_url, region_name и т.п. при MinIO).
    """
    return boto3.client(
        "s3",
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=getattr(settings, "AWS_S3_REGION_NAME", None),
    )


def generate_presigned_post(key: str, expires_in: int = 300) -> Dict[str, Any]:
    """
    Создаёт presigned POST для загрузки файла напрямую в бакет MEDIA_BUCKET_NAME.
    """
    client = get_s3_client()
    return client.generate_presigned_post(
        Bucket=settings.MEDIA_BUCKET_NAME,
        Key=key,
        ExpiresIn=expires_in,
    )
