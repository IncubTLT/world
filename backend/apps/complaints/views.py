from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from apps.utils.permissions import IsAdminModeratorOrOwner, IsAdminOrModerator, IsOwnerOrCreator
from .models import Complaint
from .serializers import ComplaintSerializer


@extend_schema_view(
    list=extend_schema(summary=_("Список жалоб"), tags=["complaints"]),
    retrieve=extend_schema(summary=_("Получить жалобу"), tags=["complaints"]),
    create=extend_schema(summary=_("Создать жалобу"), tags=["complaints"]),
    update=extend_schema(summary=_("Обновить жалобу"), tags=["complaints"]),
    partial_update=extend_schema(summary=_("Частично обновить жалобу"), tags=["complaints"]),
    destroy=extend_schema(summary=_("Удалить жалобу"), tags=["complaints"]),
)
class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.select_related("author", "content_type")
    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrCreator]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_permissions(self):
        if self.action in {"update", "partial_update"}:
            return [IsAdminOrModerator()]
        if self.action == "destroy":
            return [IsAdminModeratorOrOwner()]
        return [permission() for permission in self.permission_classes]
