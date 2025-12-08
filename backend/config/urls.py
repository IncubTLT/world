from apps.users.views import RequestCodeAPIView, VerifyCodeAPIView
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/request-code/", RequestCodeAPIView.as_view(), name="auth-request-code"),
    path("auth/verify-code/", VerifyCodeAPIView.as_view(), name="auth-verify-code"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # API-роуты
    # path("api/", include("apps.users.urls")),
    # path("api/", include("apps.places.urls")),
    # path("api/", include("apps.trips.urls")),
    # path("api/", include("apps.reviews.urls")),
    # path("api/", include("apps.messaging.urls")),
    # path("api/", include("apps.social.urls")),
    # path("api/", include("apps.complaints.urls")),

    # OpenAPI-схема (сырое описание, JSON/YAML)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # ReDoc (альтернативный красивый UI)
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
