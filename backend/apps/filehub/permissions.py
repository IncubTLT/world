from django.utils.translation import gettext_lazy as _
from rest_framework import permissions

from .models import MediaFile


class MediaFilePermission(permissions.BasePermission):
    """
    Ограничение доступа на уровне объекта:
    - PUBLIC: всем;
    - AUTH: любому авторизованному;
    - PRIVATE: только владельцу и staff.
    """

    message = _("Нет прав доступа к этому медиа-файлу.")

    def has_object_permission(self, request, view, obj: MediaFile) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        if obj.visibility == MediaFile.Visibility.PUBLIC:
            return True

        if not request.user.is_authenticated:
            return False

        if obj.visibility == MediaFile.Visibility.AUTH:
            return True

        if obj.visibility == MediaFile.Visibility.PRIVATE:
            return bool(obj.owner_id and obj.owner_id == request.user.id) or request.user.is_staff  # pyright: ignore[reportAttributeAccessIssue]

        return False
