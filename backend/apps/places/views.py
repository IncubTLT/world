from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db.models import Avg, Count, Q

from apps.utils.permissions import IsOwnerOrCreator

from .models import Place
from .serializers import PlaceSerializer


@extend_schema_view(
    list=extend_schema(summary=_("Список мест"), tags=["places"]),
    retrieve=extend_schema(summary=_("Получить место"), tags=["places"]),
    create=extend_schema(summary=_("Создать место"), tags=["places"]),
    update=extend_schema(summary=_("Обновить место"), tags=["places"]),
    partial_update=extend_schema(summary=_("Частично обновить место"), tags=["places"]),
    destroy=extend_schema(summary=_("Удалить место"), tags=["places"]),
)
class PlaceViewSet(viewsets.ModelViewSet):
    queryset = (
        Place.objects.select_related("created_by", "place_type")
        .prefetch_related("geo_coverages__coverage", "media_attachments__media_file")
        .annotate(
            rating_avg=Avg("reviews__rating", filter=Q(reviews__is_hidden=False)),
            rating_count=Count("reviews", filter=Q(reviews__is_hidden=False)),
        )
    )
    serializer_class = PlaceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrCreator]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
