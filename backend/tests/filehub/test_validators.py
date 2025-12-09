import pytest
from django.conf import settings
from rest_framework import serializers

from apps.filehub.models import MediaFile
from apps.filehub.validators import (
    validate_filename_and_type,
    validate_size_limit,
)


@pytest.mark.parametrize(
    "original_name,file_type,content_type",
    [
        ("photo.jpg", MediaFile.FileType.IMAGE, "image/jpeg"),
        ("photo.jpeg", MediaFile.FileType.IMAGE, "image/jpeg"),
        ("avatar.png", MediaFile.FileType.IMAGE, "image/png"),
        ("doc.pdf", MediaFile.FileType.DOCUMENT, "application/pdf"),
    ],
)
def test_validate_filename_and_type_ok(original_name, file_type, content_type):
    validate_filename_and_type(
        original_name=original_name,
        file_type=file_type,
        content_type=content_type,
    )


@pytest.mark.parametrize(
    "original_name,file_type",
    [
        ("shell.php", MediaFile.FileType.IMAGE),
        ("virus.exe", MediaFile.FileType.DOCUMENT),
        ("script.js", MediaFile.FileType.OTHER),
    ],
)
def test_validate_filename_and_type_forbidden_extensions(original_name, file_type):
    with pytest.raises(serializers.ValidationError) as exc:
        validate_filename_and_type(
            original_name=original_name,
            file_type=file_type,
            content_type="application/octet-stream",
        )

    # ✅ код лежит в detail / get_codes(), а не в exc.value.code
    assert isinstance(exc.value.detail, list)
    assert exc.value.detail[0].code == "forbidden_extension"
    # или:
    # assert exc.value.get_codes()[0] == "forbidden_extension"


def test_validate_filename_and_type_bad_extension_for_image():
    with pytest.raises(serializers.ValidationError) as exc:
        validate_filename_and_type(
            original_name="weird.pdf",
            file_type=MediaFile.FileType.IMAGE,
            content_type="application/pdf",
        )

    assert exc.value.detail[0].code == "bad_extension"
    assert "расширения" in str(exc.value.detail[0]).lower()


def test_validate_filename_and_type_bad_mime_for_image():
    with pytest.raises(serializers.ValidationError) as exc:
        validate_filename_and_type(
            original_name="photo.jpg",
            file_type=MediaFile.FileType.IMAGE,
            content_type="application/pdf",
        )

    assert exc.value.detail[0].code == "bad_mime"


@pytest.mark.parametrize(
    "file_type,limit_mb,size_bytes,is_ok",
    [
        (MediaFile.FileType.IMAGE, 15, 10 * 1024 * 1024, True),
        (MediaFile.FileType.IMAGE, 15, 16 * 1024 * 1024, False),
        (MediaFile.FileType.DOCUMENT, 50, 49 * 1024 * 1024, True),
        (MediaFile.FileType.DOCUMENT, 50, 51 * 1024 * 1024, False),
    ],
)
def test_validate_size_limit_respects_defaults(settings, file_type, limit_mb, size_bytes, is_ok):
    if hasattr(settings, "FILEHUB_MAX_SIZE_OVERRIDES"):
        delattr(settings, "FILEHUB_MAX_SIZE_OVERRIDES")

    if is_ok:
        validate_size_limit(size_bytes, file_type=file_type)
    else:
        with pytest.raises(serializers.ValidationError) as exc:
            validate_size_limit(size_bytes, file_type=file_type)

        assert exc.value.detail[0].code == "too_large"


def test_validate_size_limit_with_overrides(settings):
    settings.FILEHUB_MAX_SIZE_OVERRIDES = {
        MediaFile.FileType.IMAGE: 1,  # 1 МБ
    }

    # 0.5 МБ ок
    validate_size_limit(512 * 1024, file_type=MediaFile.FileType.IMAGE)

    # 2 МБ — уже нельзя
    with pytest.raises(serializers.ValidationError) as exc:
        validate_size_limit(2 * 1024 * 1024, file_type=MediaFile.FileType.IMAGE)

    assert exc.value.detail[0].code == "too_large"
