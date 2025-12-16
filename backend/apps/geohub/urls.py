from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GeoCoverageBindingViewSet, GeoCoverageViewSet, PlaceTypeViewSet

router = DefaultRouter()
router.register("coverages", GeoCoverageViewSet, basename="geo-coverage")
router.register(
    "coverage-bindings",
    GeoCoverageBindingViewSet,
    basename="geo-coverage-binding",
)
router.register("place-types", PlaceTypeViewSet, basename="place-type")

urlpatterns = [
    path("", include(router.urls)),
]
