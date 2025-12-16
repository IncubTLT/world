from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import GeoCoverage, GeoCoverageBinding, PlaceType
from .serializers import (GeoCoverageBindingCreateSerializer,
                          GeoCoverageBindingReadSerializer,
                          GeoCoverageDetailSerializer, GeoCoverageSerializer,
                          PlaceTypeSerializer)


def _content_type_from_request(request):
    app_label = request.query_params.get("target_app_label")
    model = request.query_params.get("target_model")
    if not (app_label and model):
        return None
    try:
        return ContentType.objects.get(app_label=app_label, model=model)
    except ContentType.DoesNotExist:
        return None


@extend_schema_view(
    list=extend_schema(
        summary=_("Список точек покрытия"),
        parameters=[
            OpenApiParameter(
                name="target_app_label",
                description=_("Фильтр по app_label цели привязки."),
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="target_model",
                description=_("Фильтр по model_name цели привязки."),
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="target_object_id",
                description=_("Фильтр по ID объекта, к которому привязана точка."),
                required=False,
                type=int,
            ),
        ],
    ),
    create=extend_schema(summary=_("Создать точку покрытия")),
    retrieve=extend_schema(summary=_("Получить точку покрытия с привязками")),
    update=extend_schema(summary=_("Обновить точку покрытия")),
    partial_update=extend_schema(summary=_("Частично обновить точку покрытия")),
    destroy=extend_schema(summary=_("Удалить точку покрытия")),
)
class GeoCoverageViewSet(viewsets.ModelViewSet):
    queryset = GeoCoverage.objects.all().prefetch_related("links__content_type")
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return GeoCoverageDetailSerializer
        return GeoCoverageSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        ct = _content_type_from_request(self.request)
        obj_id = self.request.query_params.get("target_object_id")
        if ct and obj_id:
            qs = qs.filter(links__content_type=ct, links__object_id=obj_id)
        return qs


@extend_schema_view(
    list=extend_schema(
        summary=_("Список привязок точек покрытия к объектам"),
        parameters=[
            OpenApiParameter(
                name="coverage",
                description=_("Фильтр по ID точки покрытия."),
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="target_app_label",
                description=_("Фильтр по app_label цели привязки."),
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="target_model",
                description=_("Фильтр по model_name цели привязки."),
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="target_object_id",
                description=_("Фильтр по ID объекта, к которому привязана точка."),
                required=False,
                type=int,
            ),
        ],
    ),
    create=extend_schema(summary=_("Создать привязку точки покрытия к объекту")),
    destroy=extend_schema(summary=_("Удалить привязку точки покрытия к объекту")),
)
class GeoCoverageBindingViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = GeoCoverageBinding.objects.select_related("coverage", "content_type")
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == "create":
            return GeoCoverageBindingCreateSerializer
        return GeoCoverageBindingReadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        coverage_id = self.request.query_params.get("coverage")
        if coverage_id:
            qs = qs.filter(coverage_id=coverage_id)

        ct = _content_type_from_request(self.request)
        obj_id = self.request.query_params.get("target_object_id")
        if ct:
            qs = qs.filter(content_type=ct)
        if obj_id:
            qs = qs.filter(object_id=obj_id)
        return qs


@extend_schema_view(
    list=extend_schema(summary=_("Список типов местности")),
    retrieve=extend_schema(summary=_("Получить тип местности")),
    create=extend_schema(summary=_("Создать тип местности")),
    update=extend_schema(summary=_("Обновить тип местности")),
    partial_update=extend_schema(summary=_("Частично обновить тип местности")),
    destroy=extend_schema(summary=_("Удалить тип местности")),
)
class PlaceTypeViewSet(viewsets.ModelViewSet):
    serializer_class = PlaceTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = PlaceType.objects.all()
        # На фронте показываем только активные типы; админ/стафф видит все.
        if not (self.request.user and self.request.user.is_staff):
            qs = qs.filter(is_active=True)
        return qs
