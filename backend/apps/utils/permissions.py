from rest_framework import permissions


class IsAdminOrModerator(permissions.BasePermission):
    """
    Доступ для пользователей с ролью admin/moderator или staff/superuser.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        role = getattr(user, "role", None)
        return user.is_superuser or user.is_staff or role in ("admin", "moderator")


class IsOwnerOrCreator(permissions.BasePermission):
    """
    Разрешает изменение только владельцу/создателю объекта.
    Использует поля owner, author, created_by или trip.owner.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False

        owner_id = getattr(obj, "owner_id", None) or getattr(obj, "author_id", None)
        creator_id = getattr(obj, "created_by_id", None)
        author = getattr(obj, "author", None)
        owner = getattr(obj, "owner", None)
        user_fk_id = getattr(obj, "user_id", None)
        trip = getattr(obj, "trip", None)

        if owner_id is not None and owner_id == user.id:
            return True
        if creator_id is not None and creator_id == user.id:
            return True
        if user_fk_id is not None and user_fk_id == user.id:
            return True
        if author and getattr(author, "id", None) == user.id:
            return True
        if owner and getattr(owner, "id", None) == user.id:
            return True
        if trip and getattr(trip, "owner_id", None) is not None:
            return trip.owner_id == user.id
        return False


class IsAdminModeratorOrOwner(permissions.BasePermission):
    """
    Доступ, если пользователь админ/модератор (роль или staff/superuser) либо автор объекта.
    """

    def has_permission(self, request, view):
        # для небезопасных методов требуется авторизация
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        admin_check = IsAdminOrModerator().has_permission(request, view)
        if admin_check:
            return True
        owner_check = IsOwnerOrCreator().has_object_permission(request, view, obj)
        return owner_check
