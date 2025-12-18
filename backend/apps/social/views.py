from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from apps.utils.permissions import IsOwnerOrCreator
from .models import Activity, Follow
from .serializers import ActivitySerializer, FollowSerializer


@extend_schema_view(
    list=extend_schema(summary=_("Список подписок"), tags=["social"]),
    create=extend_schema(summary=_("Подписаться"), tags=["social"]),
    destroy=extend_schema(
        summary=_("Отписаться"),
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description=_("ID подписки"),
            )
        ],
        tags=["social"],
    ),
)
class FollowViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = FollowSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "id"
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return Follow.objects.none()
        return Follow.objects.filter(follower=user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary=_("Лента активности"),
        description=_(
            "События от пользователей, на которых подписан текущий пользователь, "
            "плюс рекомендованные события (is_recommended=True)."
        ),
        tags=["social"],
    )
)
class ActivityFeedViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        qs = Activity.objects.select_related("actor", "content_type")
        if user and user.is_authenticated:
            following_ids = Follow.objects.filter(follower=user).values_list("target_id", flat=True)
            qs = qs.filter(Q(actor_id__in=following_ids) | Q(is_recommended=True))
        else:
            qs = qs.filter(is_recommended=True)
        return qs.order_by("-created_at")
