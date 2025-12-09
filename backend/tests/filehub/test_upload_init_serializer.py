import pytest
from apps.filehub.models import MediaAttachment, MediaFile
from apps.filehub.serializers import UploadInitSerializer
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers


def test_upload_init_serializer_valid_minimal():
    data = {
        "files": [
            {
                "original_name": "photo.jpg",
                "file_type": MediaFile.FileType.IMAGE,
                "content_type": "image/jpeg",
            }
        ]
    }

    serializer = UploadInitSerializer(data=data)
    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_upload_init_serializer_with_target_object_ok():
    """
    Проверяем, что при указании target_* создаётся корректный ContentType.
    """
    UserModel = get_user_model()
    ct = ContentType.objects.get_for_model(UserModel)

    data = {
        "files": [
            {
                "original_name": "avatar.png",
                "file_type": MediaFile.FileType.IMAGE,
                "content_type": "image/png",
                "target_app_label": ct.app_label,
                "target_model": ct.model,
                "target_object_id": 1,
                "role": MediaAttachment.Role.AVATAR,
            }
        ]
    }

    serializer = UploadInitSerializer(data=data)
    assert serializer.is_valid(), serializer.errors

    file_item = serializer.validated_data["files"][0]
    assert file_item["target_content_type"] == ct


def test_upload_init_serializer_target_object_partial_fails():
    data = {
        "files": [
            {
                "original_name": "avatar.png",
                "file_type": MediaFile.FileType.IMAGE,
                "content_type": "image/png",
                "target_app_label": "auth",
                # target_model отсутствует
                "target_object_id": 1,
            }
        ]
    }

    serializer = UploadInitSerializer(data=data)
    assert not serializer.is_valid()
    assert "files" in serializer.errors


def test_upload_init_serializer_forbidden_extension():
    data = {
        "files": [
            {
                "original_name": "shell.php",
                "file_type": MediaFile.FileType.IMAGE,
                "content_type": "application/x-php",
            }
        ]
    }

    serializer = UploadInitSerializer(data=data)
    assert not serializer.is_valid()
