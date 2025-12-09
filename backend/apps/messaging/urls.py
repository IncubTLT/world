from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChatRoomViewSet

app_name = "messaging"

router = DefaultRouter()
router.register("rooms", ChatRoomViewSet, basename="chat-room")

urlpatterns = [
    path("", include(router.urls)),
]
