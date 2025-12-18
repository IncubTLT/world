from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import (OpenApiExample, OpenApiParameter,
                                   extend_schema, extend_schema_view)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.utils.permissions import IsOwnerOrCreator
from .models import Trip, TripPoint
from .serializers import TripPointSerializer, TripSerializer


@extend_schema_view(
    list=extend_schema(
        summary=_("Список маршрутов"),
        description=_("Возвращает маршруты (публичные или свои) с вложенным деревом точек в поле points."),
        tags=["trips"],
    ),
    retrieve=extend_schema(
        summary=_("Получить маршрут с точками"),
        description=_("Дерево точек в поле points -> children."),
        tags=["trips"],
        examples=[
            OpenApiExample(
                "Маршрут с точками",
                value={
                    "id": 1,
                    "owner": 10,
                    "title": "Моё путешествие",
                    "short_description": "3 дня в горах",
                    "description": "Полный маршрут",
                    "is_public": True,
                    "is_hidden": False,
                    "source_trip": None,
                    "points": [
                        {
                            "id": 101,
                            "trip": 1,
                            "place": 5,
                            "note": "Старт",
                            "path": "0001",
                            "depth": 1,
                            "children": [
                                {
                                    "id": 102,
                                    "trip": 1,
                                    "place": None,
                                    "note": "Ответвление",
                                    "path": "00010001",
                                    "depth": 2,
                                    "children": [],
                                }
                            ],
                        }
                    ],
                    "created_at": "2025-12-16T12:00:00Z",
                    "updated_at": "2025-12-16T12:00:00Z",
                },
                response_only=True,
            )
        ],
    ),
    create=extend_schema(
        summary=_("Создать маршрут"),
        tags=["trips"],
        examples=[
            OpenApiExample(
                "Создание маршрута",
                value={
                    "title": "Трип по Европе",
                    "short_description": "Быстрый тур",
                    "description": "Подробности маршрута",
                    "is_public": True,
                },
                request_only=True,
            )
        ],
    ),
    update=extend_schema(summary=_("Обновить маршрут"), tags=["trips"]),
    partial_update=extend_schema(summary=_("Частично обновить маршрут"), tags=["trips"]),
    destroy=extend_schema(summary=_("Удалить маршрут"), tags=["trips"]),
)
class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all().select_related("owner", "source_trip").prefetch_related("points__place")
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrCreator]

    def get_serializer_class(self):
        return TripSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated], serializer_class=None)
    @extend_schema(
        summary=_("Скопировать маршрут себе"),
        description=_(
            "Создаёт копию маршрута для текущего пользователя. "
            "copy_points=true — копирует дерево точек, иначе создаёт пустой маршрут."
        ),
        request=None,
        responses=TripSerializer,
        tags=["trips"],
        examples=[
            OpenApiExample(
                "Копирование маршрута",
                value={"copy_points": True},
                request_only=True,
            ),
            OpenApiExample(
                "Ответ копирования",
                value={
                    "id": 99,
                    "owner": 10,
                    "title": "Трип по Европе",
                    "short_description": "Быстрый тур",
                    "description": "Подробности маршрута",
                    "is_public": False,
                    "is_hidden": False,
                    "source_trip": 12,
                    "points": [],
                    "created_at": "2025-12-16T12:00:00Z",
                    "updated_at": "2025-12-16T12:00:00Z",
                },
                response_only=True,
            ),
        ],
    )
    def fork(self, request, pk=None):
        """
        Создать копию маршрута для текущего пользователя.
        copy_points: bool (по умолчанию True) — копировать точки.
        """
        original: Trip = self.get_object()
        copy_points = bool(request.data.get("copy_points", True))
        with transaction.atomic():
            new_trip = Trip.objects.create(
                owner=request.user,
                title=original.title,
                short_description=original.short_description,
                description=original.description,
                is_public=False,
                is_hidden=False,
                source_trip=original,
            )

            if copy_points:
                # Копируем дерево точек сохраняя иерархию
                id_map = {}
                for node in original.points.all().order_by("path"):
                    parent = node.get_parent()
                    parent_new = id_map.get(parent.id) if parent else None
                    data = {
                        "trip": new_trip,
                        "place": node.place,
                        "note": node.note,
                    }
                    if parent_new:
                        id_map[node.id] = parent_new.add_child(**data)
                    else:
                        id_map[node.id] = TripPoint.add_root(**data)

        serializer = self.get_serializer(new_trip)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        summary=_("Список точек маршрута"),
        tags=["trip-points"],
        parameters=[
            OpenApiParameter(
                name="trip",
                description=_("ID маршрута для фильтрации точек."),
                required=False,
                type=int,
            )
        ],
        description=_("Возвращает все точки маршрута в плоском списке, отсортированном по path."),
    ),
    retrieve=extend_schema(summary=_("Получить точку маршрута"), tags=["trip-points"]),
    create=extend_schema(
        summary=_("Создать точку маршрута"),
        tags=["trip-points"],
        description=_(
            "Если parent не указан — создаётся корневой узел. "
            "Если указан parent — создаётся дочерний узел внутри того же маршрута."
        ),
        examples=[
            OpenApiExample(
                "Корневая точка",
                value={"trip": 1, "place": 5, "note": "Стартовая точка"},
                request_only=True,
            ),
            OpenApiExample(
                "Дочерняя точка",
                value={"trip": 1, "parent": 101, "note": "Ветка маршрута"},
                request_only=True,
            ),
        ],
    ),
    update=extend_schema(summary=_("Обновить точку маршрута"), tags=["trip-points"]),
    partial_update=extend_schema(summary=_("Частично обновить точку маршрута"), tags=["trip-points"]),
    destroy=extend_schema(summary=_("Удалить точку маршрута"), tags=["trip-points"]),
)
class TripPointViewSet(viewsets.ModelViewSet):
    serializer_class = TripPointSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrCreator]

    def get_queryset(self):
        qs = TripPoint.objects.select_related("trip", "place").order_by("path")
        trip_id = self.request.query_params.get("trip")
        if trip_id:
            qs = qs.filter(trip_id=trip_id)
        return qs

    def perform_create(self, serializer):
        trip = serializer.validated_data["trip"]
        if trip.owner_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(_("Можно добавлять точки только в свой маршрут."))
        serializer.save()
