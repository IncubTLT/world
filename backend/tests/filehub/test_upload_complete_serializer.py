import pytest
from rest_framework import serializers

from apps.filehub.models import MediaFile
from apps.filehub.serializers import UploadCompleteSerializer


@pytest.mark.django_db
def test_upload_complete_serializer_ok_for_small_image():
    media = MediaFile.objects.create(
        key="images/private/test.jpg",
        file_type=MediaFile.FileType.IMAGE,
        visibility=MediaFile.Visibility.PRIVATE,
    )

    data = {
        "media_file_id": str(media.id),
        "size_bytes": 1024 * 1024,  # 1 МБ
    }

    serializer = UploadCompleteSerializer(data=data)
    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_upload_complete_serializer_size_too_large(settings):
    # Ужесточим лимит для image до 1 МБ
    settings.FILEHUB_MAX_SIZE_OVERRIDES = {
        MediaFile.FileType.IMAGE: 1,
    }

    media = MediaFile.objects.create(
        key="images/private/test.jpg",
        file_type=MediaFile.FileType.IMAGE,
        visibility=MediaFile.Visibility.PRIVATE,
    )

    data = {
        "media_file_id": str(media.id),
        "size_bytes": 5 * 1024 * 1024,  # 5 МБ
    }

    serializer = UploadCompleteSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)
