from django.urls import include, path

urlpatterns = [
    path("users/", include("apps.users.urls")),
    path("filehub/", include("apps.filehub.urls")),
    path("messaging/", include("apps.messaging.urls")),
    path("ai/", include("apps.ai.urls", namespace="ai")),
    path("geohub/", include("apps.geohub.urls")),
    path("places/", include("apps.places.urls")),
    # path("trips/", include("apps.trips.urls")),
    # path("reviews/", include("apps.reviews.urls")),
    # path("social/", include("apps.social.urls")),
    # path("complaints/", include("apps.complaints.urls")),
]
