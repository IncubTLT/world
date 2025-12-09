import uuid

import pytest
from apps.filehub.models import MediaAttachment, MediaFile
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_upload_init_creates_mediafile_and_returns_presigned_post(monkeypatch, regular_user):
    client = APIClient()
    client.force_authenticate(user=regular_user)

    def fake_generate_presigned_post(key, expires_in=300):
        return {
            "url": "https://example.com/upload",
            "fields": {
                "key": "dummy-key",
                "policy": "BASE64_POLICY",
            },
        }

    def fake_build_media_key(**kwargs):
        return "images/private/test/uuid.jpg"

    # важно: патчим именно тот модуль, где эти функции ИМПОРТИРОВАНЫ
    monkeypatch.setattr(
        "apps.filehub.views.generate_presigned_post",
        fake_generate_presigned_post,
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
    assert result_item["upload"]["url"] == "https://example.com/upload"

    mf = MediaFile.objects.get(id=result_item["media_file_id"])
    # 🔧 тут должен быть regular_user, а не user
    assert mf.owner == regular_user
    assert mf.key == "images/private/test/uuid.jpg"
    assert mf.file_type == MediaFile.FileType.IMAGE


@pytest.mark.django_db
def test_upload_init_creates_media_attachment(monkeypatch, django_user_model, regular_user):
    """
    Проверяем кейс, когда сразу привязываем медиа к объекту.
    """
    UserModel = django_user_model

    client = APIClient()
    client.force_authenticate(user=regular_user)

    ct = ContentType.objects.get_for_model(UserModel)

    def fake_generate_presigned_post(key, expires_in=300):
        return {
            "url": "https://example.com/upload",
            "fields": {"key": "dummy-key"},
        }

    def fake_build_media_key(**kwargs):
        return "images/private/users/user/1/test.jpg"

    monkeypatch.setattr(
        "apps.filehub.views.generate_presigned_post",
        fake_generate_presigned_post,
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
                # 🔧 вместо owner.id — regular_user.id
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
