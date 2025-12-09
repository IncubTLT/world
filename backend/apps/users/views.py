from __future__ import annotations

from typing import Any, cast

from apps.users.redis_code import CodeManager
from apps.users.utils import send_activation_email
from apps.utils.utilities import get_client_ip
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import (OpenApiExample, OpenApiResponse,
                                   extend_schema, extend_schema_view)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (RequestCodeSerializer, UserSerializer,
                          VerifyCodeSerializer)

User = get_user_model()


@extend_schema(
    tags=["auth"],
    summary=_("Запрос кода для входа по email"),
    description=_(
        "Принимает email пользователя, генерирует одноразовый код и отправляет его на почту. "
        "Используется для входа без пароля."
    ),
    request=RequestCodeSerializer,
    responses={
        200: OpenApiResponse(
            description=_("Код успешно отправлен на email (или будет отправлен в фоне)."),
            examples=[
                OpenApiExample(
                    "Успех",
                    value={"detail": "Код отправлен на указанный email."},
                    response_only=True,
                )
            ],
        ),
        400: OpenApiResponse(
            description=_("Ошибка валидации (невалидный email или отсутствует поле)."),
        ),
        429: OpenApiResponse(
            description=_("Слишком много запросов с этого IP/email за короткий период."),
        ),
    },
)
class RequestCodeAPIView(APIView):
    """
    POST /api/auth/request-code/

    { "email": "user@example.com" }

    Отправляет одноразовый код на email с учётом лимитов по IP.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        serializer: RequestCodeSerializer = RequestCodeSerializer(data=request.data)  # pyright: ignore[reportAssignmentType]
        serializer.is_valid(raise_exception=True)

        # validated_data типизировано как dict | _empty, поэтому cast
        validated = cast(dict[str, Any], serializer.validated_data)

        email_raw = validated.get("email")
        if not isinstance(email_raw, str):
            return Response(
                {"detail": "Неверные данные в запросе."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = email_raw.lower()
        code_manager = CodeManager()

        ip = get_client_ip(request) or "unknown"
        ip_key = f"request_code_ip:{ip}"
        redis_key = f"login_code:{email}"

        # Лимит: не более 3 запросов кода за 5 минут с одного IP
        if code_manager.is_request_limited(ip_key, limit_seconds=300, max_attempts=3):
            return Response(
                {"detail": "Повторный запрос кода возможен не ранее чем через 5 минут."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        code = code_manager.generate_code()
        code_manager.set_code(redis_key, code)

        send_activation_email(email=email, code=code)

        return Response(
            {"detail": "Код отправлен на указанный email."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["auth"],
    summary=_("Подтверждение кода и получение токенов"),
    description=_(
        "Проверяет одноразовый код для указанного email. "
        "Если пользователь ещё не существует — создаёт его. "
        "В случае успеха возвращает JWT-токены (access/refresh)."
    ),
    request=VerifyCodeSerializer,
    responses={
        200: OpenApiResponse(
            description=_("Код верный, выданы токены."),
            examples=[
                OpenApiExample(
                    "Успех",
                    value={
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    },
                    response_only=True,
                )
            ],
        ),
        400: OpenApiResponse(
            description=_("Неверный код, истёкший код или ошибка валидации."),
        ),
        404: OpenApiResponse(
            description=_("Код для этого email не найден (истёк или не запрашивался)."),
        ),
        429: OpenApiResponse(
            description=_("Превышено число попыток ввода кода."),
        ),
    },
)
class VerifyCodeAPIView(APIView):
    """
    POST /api/auth/verify-code/

    {
        "email": "user@example.com",
        "code": "123456"
    }

    Проверяет одноразовый код, создаёт/обновляет пользователя
    и возвращает пару JWT-токенов (access + refresh).
    """

    permission_classes = [permissions.AllowAny]

    def foul_message(self) -> str:
        login_url = f"http://{settings.DOMAIN}/login/"
        return (
            "Превышен лимит попыток. "
            "Попробуйте заново пройти авторизацию по ссылке: "
            f"{login_url}"
        )

    def _create_or_update_user(self, email: str) -> User:
        """
        Создаёт пользователя по email или берёт существующего.
        При успешной верификации помечаем email как подтверждённый.
        """
        user, created = User.objects.get_or_create(email=email)
        if created or not getattr(user, "email_confirmed", False):
            user.email_confirmed = True  # pyright: ignore[reportAttributeAccessIssue]
            user.save(update_fields=["email_confirmed"])
        return user

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        serializer: VerifyCodeSerializer = VerifyCodeSerializer(data=request.data)  # pyright: ignore[reportAssignmentType]
        serializer.is_valid(raise_exception=True)

        validated = cast(dict[str, Any], serializer.validated_data)

        email_raw = validated.get("email")
        code_raw = validated.get("code")

        if not isinstance(email_raw, str) or not isinstance(code_raw, str):
            return Response(
                {"detail": "Неверные данные в запросе."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = email_raw.lower()
        code = code_raw.strip()

        code_manager = CodeManager()
        ip = get_client_ip(request) or "unknown"
        ip_key = f"verify_code_ip:{ip}"
        redis_key = f"login_code:{email}"

        # Лимит попыток ввода кода: например, 5 за 5 минут
        if code_manager.is_request_limited(
            ip_key,
            limit_seconds=300,
            max_attempts=5,
        ):
            return Response(
                {
                    "detail": self.foul_message(),
                    "code": "too_many_attempts",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Проверка одноразового кода
        is_valid_code = code_manager.verify_code(redis_key, code)
        if not is_valid_code:
            return Response(
                {
                    "detail": "Неверный или истёкший код.",
                    "code": "invalid_code",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Код корректен → создаём/обновляем пользователя
        user = self._create_or_update_user(email)

        # Генерируем JWT-токены
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # Дополнительные клеймы (опционально)
        access["email"] = user.email  # pyright: ignore[reportAttributeAccessIssue]
        access["display_name"] = getattr(user, "display_name", "") or user.email  # pyright: ignore[reportAttributeAccessIssue]

        data: dict[str, Any] = {
            "access": str(access),
            "refresh": str(refresh),
            "user": {
                "id": user.id,  # pyright: ignore[reportAttributeAccessIssue]
                "email": user.email,  # pyright: ignore[reportAttributeAccessIssue]
                "display_name": getattr(user, "display_name", "") or user.email,  # pyright: ignore[reportAttributeAccessIssue]
            },
        }

        return Response(data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        tags=["users"],
        summary=_("Список пользователей"),
        description=_(
            "Возвращает список всех пользователей. "
            "Доступно только администраторам (is_staff=True)."
        ),
        responses={
            200: OpenApiResponse(response=UserSerializer(many=True)),
            403: OpenApiResponse(description=_("Недостаточно прав.")),
        },
    ),
    retrieve=extend_schema(
        tags=["users"],
        summary=_("Информация о пользователе"),
        description=_(
            "Возвращает информацию о конкретном пользователе по ID. "
            "Доступно только администраторам (is_staff=True)."
        ),
        responses={
            200: OpenApiResponse(response=UserSerializer),
            403: OpenApiResponse(description=_("Недостаточно прав.")),
            404: OpenApiResponse(description=_("Пользователь не найден.")),
        },
    ),
)
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet для пользователей.

    - admin/staff: могут смотреть список и детали по ID;
    - обычные пользователи: отдельная ручка /users/me/ (см. ниже).
    """

    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        return (
            User.objects
            .only("id", "email", "display_name")
            .order_by("id")
        )

    @extend_schema(
        tags=["users"],
        summary=_("Текущий пользователь"),
        description=_(
            "Возвращает данные текущего авторизованного пользователя. "
            "Доступно любому аутентифицированному пользователю."
        ),
        responses={
            200: OpenApiResponse(response=UserSerializer),
            401: OpenApiResponse(description=_("Не авторизован.")),
        },
        examples=[
            OpenApiExample(
                "Пример ответа",
                value={
                    "id": 123,
                    "email": "user@example.com",
                    "display_name": "user",
                },
                response_only=True,
            )
        ],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="me",
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        """
        /api/users/users/me/ (если оставить текущую схему include)
        или /api/users/me/ (если поправим роутинг, см. ниже).
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
