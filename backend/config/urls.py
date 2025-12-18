from apps.users.views import RequestCodeAPIView, VerifyCodeAPIView
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Авторизация по коду (можно позже тоже перенести под /api/auth/)
    path("auth/request-code/", RequestCodeAPIView.as_view(), name="auth-request-code"),
    path("auth/verify-code/", VerifyCodeAPIView.as_view(), name="auth-verify-code"),
    path("auth/jwt/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Единая точка входа для всего API
    path("api/", include("apps.urls")),

    # OpenAPI-схема
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # ReDoc
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
