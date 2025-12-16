from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Place
from .serializers import PlaceSerializer


@extend_schema_view(
    list=extend_schema(summary=_("Список мест")),
    retrieve=extend_schema(summary=_("Получить место")),
    create=extend_schema(summary=_("Создать место")),
    update=extend_schema(summary=_("Обновить место")),
    partial_update=extend_schema(summary=_("Частично обновить место")),
    destroy=extend_schema(summary=_("Удалить место")),
)
class PlaceViewSet(viewsets.ModelViewSet):
    queryset = (
        Place.objects.select_related("created_by", "place_type")
        .prefetch_related("geo_coverages__coverage", "media_attachments__media_file")
        .all()
    )
    serializer_class = PlaceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
