from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ActivityFeedViewSet, FollowViewSet

router = DefaultRouter()
router.register("follows", FollowViewSet, basename="follow")
router.register("feed", ActivityFeedViewSet, basename="activity-feed")

urlpatterns = [
    path("", include(router.urls)),
]
