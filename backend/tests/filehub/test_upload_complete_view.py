import pytest
from apps.filehub.models import (MediaAttachment, MediaFile, MediaFileVariant,
                                 Status)
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_upload_complete_updates_media_and_triggers_task(monkeypatch, regular_user):
    """
    Базовый happy-path:
    - владелец файла подтверждает загрузку,
    - обновляются размер/чексумма,
    - статус = UPLOADED (если есть),
    - вызывается задача обработки вариантов.
    """

    # Аккуратно добавляем статус, только если он реально есть в модели
    extra_kwargs = {}
    if hasattr(MediaFile, "Status") and any(f.name == "status" for f in MediaFile._meta.fields):
        extra_kwargs["status"] = Status.PENDING

    media = MediaFile.objects.create(
        owner=regular_user,
        key="images/private/test.jpg",
        file_type=MediaFile.FileType.IMAGE,
        visibility=MediaFile.Visibility.PRIVATE,
        **extra_kwargs,
    )

    client = APIClient()
    client.force_authenticate(user=regular_user)

    # Заглушка для таски, которая должна дернуться из UploadCompleteView
    class DummyTask:
        def __init__(self):
            self.called_with: list[str] = []

        # ⚡ Делаем асинхронным, чтобы async_to_sync был счастлив
        async def kiq(self, media_id: str):
            self.called_with.append(media_id)

    task_stub = DummyTask()

    # Патчим именно объект, импортированный во views
    monkeypatch.setattr(
        "apps.filehub.views.process_media_file_variants_task",
        task_stub,
    )

    url = reverse("filehub-upload-complete")
    payload = {
        "media_file_id": str(media.id),
        "size_bytes": 123456,
        "checksum": "deadbeef123",
    }

    response = client.post(url, data=payload, format="json")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    media.refresh_from_db()
    assert media.size_bytes == 123456
    assert media.checksum == "deadbeef123"

    # Если есть поле status — проверяем переход в UPLOADED
    if hasattr(MediaFile, "Status") and hasattr(media, "status"):
        assert media.status == Status.UPLOADED

    # Проверяем, что задача обработки действительно дернулась
    assert task_stub.called_with == [str(media.id)]


@pytest.mark.django_db
def test_upload_complete_forbidden_for_non_owner(monkeypatch, regular_user, django_user_model):
    """
    Другой пользователь не может подтверждать загрузку чужого файла.
    """
    media = MediaFile.objects.create(
        owner=regular_user,
        key="images/private/test2.jpg",
        file_type=MediaFile.FileType.IMAGE,
        visibility=MediaFile.Visibility.PRIVATE,
    )

    other_user = django_user_model.objects.create_user(
        email="other@example.com",
        password=None,
    )

    client = APIClient()
    client.force_authenticate(user=other_user)

    class DummyTask:
        # тоже делаем async, чтобы в случае бага упасть сразу
        async def kiq(self, media_id: str):
            pytest.fail("Task should not be called for foreign user")

    monkeypatch.setattr(
        "apps.filehub.views.process_media_file_variants_task",
        DummyTask(),
    )

    url = reverse("filehub-upload-complete")
    payload = {
        "media_file_id": str(media.id),
        "size_bytes": 1000,
    }

    response = client.post(url, data=payload, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    media.refresh_from_db()
    # Ничего не должно измениться
    assert media.size_bytes is None


@pytest.mark.django_db
def test_upload_complete_not_found(monkeypatch, regular_user):
    """
    Если указать несуществующий media_file_id – получаем 404.
    """
    client = APIClient()
    client.force_authenticate(user=regular_user)

    class DummyTask:
        async def kiq(self, media_id: str):
            pytest.fail("Task should not be called when media is missing")

    monkeypatch.setattr(
        "apps.filehub.views.process_media_file_variants_task",
        DummyTask(),
    )

    url = reverse("filehub-upload-complete")
    payload = {
        "media_file_id": "00000000-0000-0000-0000-000000000000",
        "size_bytes": 1000,
    }

    response = client.post(url, data=payload, format="json")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_upload_complete_too_large(settings, monkeypatch, regular_user):
    """
    Интеграционный кейс: лимит размера срабатывает на уровне сериализатора,
    а вьюха отдаёт 400.
    """
    # Ужесточаем лимит для картинок до 1 МБ
    settings.FILEHUB_MAX_SIZE_OVERRIDES = {
        MediaFile.FileType.IMAGE: 1,
    }

    media = MediaFile.objects.create(
        owner=regular_user,
        key="images/private/big.jpg",
        file_type=MediaFile.FileType.IMAGE,
        visibility=MediaFile.Visibility.PRIVATE,
    )

    client = APIClient()
    client.force_authenticate(user=regular_user)

    class DummyTask:
        async def kiq(self, media_id: str):
            pytest.fail("Task should not be called when size is too large")

    monkeypatch.setattr(
        "apps.filehub.views.process_media_file_variants_task",
        DummyTask(),
    )

    url = reverse("filehub-upload-complete")
    payload = {
        "media_file_id": str(media.id),
        "size_bytes": 5 * 1024 * 1024,  # 5 МБ – больше лимита
    }

    response = client.post(url, data=payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    data = response.json()
    # Сейчас ошибка прилетает как non_field_errors
    assert "non_field_errors" in data
    text = " ".join(str(msg) for msg in data["non_field_errors"])
    assert "слишком большой" in text.lower()


@pytest.mark.django_db
def test_mediafile_delete_cascades_to_variants_and_attachments(regular_user, django_user_model):

    user = regular_user
    ct = ContentType.objects.get_for_model(django_user_model)

    media = MediaFile.objects.create(
        owner=user,
        key="images/private/test.jpg",
        file_type=MediaFile.FileType.IMAGE,
        visibility=MediaFile.Visibility.PRIVATE,
    )

    MediaFileVariant.objects.create(
        media_file=media,
        kind=MediaFileVariant.Kind.WEBP,
        key="images/private/test.webp",
    )

    MediaAttachment.objects.create(
        content_type=ct,
        object_id=user.id,
        media_file=media,
        role=MediaAttachment.Role.AVATAR,
        is_primary=True,
    )

    media.delete()

    assert MediaFileVariant.objects.count() == 0
    assert MediaAttachment.objects.count() == 0


@pytest.mark.django_db
def test_upload_init_multiple_files_one_with_target(monkeypatch, regular_user, django_user_model):
    from apps.filehub.models import MediaAttachment, MediaFile
    from django.contrib.contenttypes.models import ContentType

    client = APIClient()
    client.force_authenticate(user=regular_user)

    ct = ContentType.objects.get_for_model(django_user_model)

    def fake_generate_presigned_post(key, expires_in=300):
        return {"url": "https://example.com/upload", "fields": {"key": "dummy"}}

    def fake_build_media_key(**kwargs):
        # можешь сделать чуть умнее, но для теста хватит
        return f"images/private/{kwargs.get('original_name', 'file')}"

    monkeypatch.setattr("apps.filehub.views.generate_presigned_post", fake_generate_presigned_post)
    monkeypatch.setattr("apps.filehub.views.build_media_key", fake_build_media_key)

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
            },
            {
                "original_name": "doc.pdf",
                "file_type": "document",
                "content_type": "application/pdf",
                "visibility": "private",
            },
        ]
    }

    response = client.post(url, data=payload, format="json")
    assert response.status_code == 201

    # 2 MediaFile
    assert MediaFile.objects.count() == 2
    # 1 attachment — только у первого
    assert MediaAttachment.objects.count() == 1
