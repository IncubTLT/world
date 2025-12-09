from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UploadInitView, UploadCompleteView, MediaFileViewSet

router = DefaultRouter()
router.register("files", MediaFileViewSet, basename="mediafile")

urlpatterns = [
    path("upload-init/", UploadInitView.as_view(), name="filehub-upload-init"),
    path("upload-complete/", UploadCompleteView.as_view(), name="filehub-upload-complete"),
    path("", include(router.urls)),
]
