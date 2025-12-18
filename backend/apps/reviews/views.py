from django.utils.translation import gettext_lazy as _
from django.db import models
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from apps.utils.permissions import IsAdminModeratorOrOwner, IsOwnerOrCreator
from .models import Review
from .serializers import ReviewSerializer


@extend_schema_view(
    list=extend_schema(summary=_("Список отзывов"), tags=["reviews"]),
    retrieve=extend_schema(summary=_("Получить отзыв"), tags=["reviews"]),
    create=extend_schema(summary=_("Создать отзыв"), tags=["reviews"]),
    update=extend_schema(summary=_("Обновить отзыв"), tags=["reviews"]),
    partial_update=extend_schema(summary=_("Частично обновить отзыв"), tags=["reviews"]),
    destroy=extend_schema(summary=_("Удалить отзыв"), tags=["reviews"]),
)
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = (
        Review.objects.select_related("author", "place")
        .prefetch_related("media_attachments__media_file")
        .order_by("-created_at")
    )
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrCreator]
    filterset_fields = ["place"]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            role = getattr(user, "role", None)
            is_mod = user.is_staff or user.is_superuser or role in ("admin", "moderator")
            if is_mod:
                return qs
            return qs.filter(models.Q(is_hidden=False) | models.Q(author=user))
        return qs.filter(is_hidden=False)

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            return [IsAdminModeratorOrOwner()]
        return [permission() for permission in self.permission_classes]
