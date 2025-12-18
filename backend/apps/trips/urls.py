from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TripPointViewSet, TripViewSet

router = DefaultRouter()
router.register("trips", TripViewSet, basename="trip")
router.register("trip-points", TripPointViewSet, basename="trip-point")

urlpatterns = [
    path("", include(router.urls)),
]
