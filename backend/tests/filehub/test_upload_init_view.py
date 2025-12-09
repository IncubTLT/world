import pytest
from apps.filehub.models import MediaAttachment, MediaFile
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_upload_init_creates_mediafile_and_returns_presigned_put(
    monkeypatch,
    regular_user,
):
    client = APIClient()
    client.force_authenticate(user=regular_user)

    def fake_generate_presigned_put(*args, **kwargs):
        # Эмулируем новый формат: url + method + headers
        return {
            "url": "https://example.com/upload",
            "method": "PUT",
            "headers": {
                "Content-Type": "image/jpeg",
            },
        }

    def fake_build_media_key(**kwargs):
        return "images/private/test/uuid.jpg"

    # ВАЖНО: патчим именно тот модуль, где функции ИМПОРТИРОВАНЫ во view
    monkeypatch.setattr(
        "apps.filehub.views.generate_presigned_put",
        fake_generate_presigned_put,
    )
    monkeypatch.setattr(
        "apps.filehub.views.build_media_key",
        fake_build_media_key,
    )

    url = reverse("filehub-upload-init")
    payload = {
        "files": [
            {
                "original_name": "photo.jpg",
                "file_type": "image",
                "content_type": "image/jpeg",
                "visibility": "private",
            }
        ]
    }

    response = client.post(url, data=payload, format="json")
    assert response.status_code == 201
    body = response.json()

    assert "files" in body
    assert len(body["files"]) == 1

    result_item = body["files"][0]
    assert result_item["key"] == "images/private/test/uuid.jpg"
    assert result_item["visibility"] == "private"

    # Новый формат upload
    upload = result_item["upload"]
    assert upload["url"] == "https://example.com/upload"
    assert upload["method"] == "PUT"
    assert upload["headers"]["Content-Type"] == "image/jpeg"

    mf = MediaFile.objects.get(id=result_item["media_file_id"])
    assert mf.owner == regular_user
    assert mf.key == "images/private/test/uuid.jpg"
    assert mf.file_type == MediaFile.FileType.IMAGE


@pytest.mark.django_db
def test_upload_init_creates_media_attachment(
    monkeypatch,
    django_user_model,
    regular_user,
):
    """
    Проверяем кейс, когда сразу привязываем медиа к объекту.
    """
    UserModel = django_user_model

    client = APIClient()
    client.force_authenticate(user=regular_user)

    ct = ContentType.objects.get_for_model(UserModel)

    def fake_generate_presigned_put(*args, **kwargs):
        return {
            "url": "https://example.com/upload",
            "method": "PUT",
            "headers": {
                "Content-Type": "image/png",
            },
        }

    def fake_build_media_key(**kwargs):
        return "images/private/users/user/1/test.jpg"

    monkeypatch.setattr(
        "apps.filehub.views.generate_presigned_put",
        fake_generate_presigned_put,
    )
    monkeypatch.setattr(
        "apps.filehub.views.build_media_key",
        fake_build_media_key,
    )

    url = reverse("filehub-upload-init")
    payload = {
        "files": [
            {
                "original_name": "avatar.png",
                "file_type": "image",
                "content_type": "image/png",
                "visibility": "private",
                "target_app_label": ct.app_label,
                "target_model": ct.model,
                "target_object_id": regular_user.id,
                "role": "avatar",
            }
        ]
    }

    response = client.post(url, data=payload, format="json")
    assert response.status_code == 201

    mf = MediaFile.objects.first()
    assert mf is not None

    attachment = MediaAttachment.objects.first()
    assert attachment is not None
    assert attachment.media_file == mf
    assert attachment.role == MediaAttachment.Role.AVATAR
    assert attachment.object_id == regular_user.id
