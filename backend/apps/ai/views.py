from django.db.models import Q
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.models import (
    Consumer,
    GptModels,
    TextTransactions,
    UserGptModels,
)
from .serializers import (
    AIHistoryResponseSerializer,
    BalanceSerializer,
    GptModelPriceSerializer,
    SimpleSuccessSerializer,
    TextTransactionSerializer,
    UserGptModelsSerializer,
    UserModelsProfileResponseSerializer,
)


class AIHistoryView(generics.ListAPIView):
    """
    Возвращает историю запросов к ИИ для текущего пользователя.
    """

    serializer_class = TextTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            TextTransactions.objects
            .filter(
                user=self.request.user,
                consumer=Consumer.FAST_CHAT,
            )
            .exclude(answer__isnull=True)
            .exclude(answer__exact="")
            .order_by("-created_at")
        )

    @extend_schema(
        tags=["AI"],
        summary=_("Получить историю запросов к ИИ"),
        description=_(
            "Возвращает до 20 последних вопросов и ответов пользователя к AI "
            "для потребителя FAST_CHAT в хронологическом порядке (от старого к новому)."
        ),
        responses={200: AIHistoryResponseSerializer},
    )
    def list(self, request, *args, **kwargs):
        """
        Возвращает объект вида:
        {
            "history": [
                {"id": ..., "question": "...", "answer": "...", "created_at": "..."},
                ...
            ]
        }
        """
        queryset = list(self.get_queryset()[:20])
        queryset.reverse()

        serializer = self.get_serializer(queryset, many=True)
        wrapper = AIHistoryResponseSerializer({"history": serializer.data})
        return Response(wrapper.data)


class UserModelsProfileView(generics.RetrieveUpdateAPIView):
    """
    Профиль GPT-моделей для текущего пользователя.
    """

    serializer_class = UserGptModelsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self) -> UserGptModels:
        """
        Логика совпадает с исходным UpdateView:
        - создаём/берём UserGptModels;
        - по балансу определяем, какие модели разрешены;
        - обновляем approved_models, если список изменился.
        """
        user = self.request.user
        obj, _ = UserGptModels.objects.get_or_create(user=user)

        user_balance_manager = getattr(user, "account_balance", None)
        user_balance = user_balance_manager.last() if user_balance_manager is not None else None

        all_models = GptModels.objects.all()

        if user_balance and user_balance.remaining_balance > 0:
            approved_qs = all_models.filter(consumer=Consumer.FAST_CHAT)
        else:
            approved_qs = all_models.filter(
                is_free=True,
                consumer=Consumer.FAST_CHAT,
            )

        approved_ids = set(approved_qs.values_list("id", flat=True))
        current_ids = set(obj.approved_models.values_list("id", flat=True))

        if approved_ids != current_ids:
            obj.approved_models.set(approved_qs)

        return obj

    def _build_profile_response_data(self, instance: UserGptModels) -> dict:
        """
        Собирает финальный ответ:
        - базовые поля UserGptModelsSerializer;
        - model_prices;
        - balance.
        """
        # базовые поля профиля
        base_data = dict(self.get_serializer(instance).data)

        # модели с ценами (аналог get_filtered_models)
        model_prices_qs = (
            GptModels.objects
            .filter(
                Q(incoming_price__gt=0) | Q(outgoing_price__gt=0),
                Q(consumer=Consumer.FAST_CHAT) | Q(consumer=Consumer.IMAGE),
            )
            .distinct("title")
        )
        model_prices = GptModelPriceSerializer(
            model_prices_qs,
            many=True,
            context=self.get_serializer_context(),
        ).data

        # баланс пользователя
        user_balance_manager = getattr(self.request.user, "account_balance", None)
        user_balance = user_balance_manager.last() if user_balance_manager is not None else None
        remaining_balance = getattr(user_balance, "remaining_balance", None)

        balance_data = BalanceSerializer(
            {"remaining_balance": remaining_balance}
        ).data

        base_data["model_prices"] = model_prices
        base_data["balance"] = balance_data
        return base_data

    @extend_schema(
        tags=["AI"],
        summary=_("Получить профиль моделей пользователя"),
        description=_(
            "Возвращает активную модель и промпт, список разрешённых моделей, "
            "а также список моделей с ценами и краткую информацию о балансе."
        ),
        responses={200: UserModelsProfileResponseSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = self._build_profile_response_data(instance)
        return Response(data)

    @extend_schema(
        tags=["AI"],
        summary=_("Обновить профиль моделей пользователя"),
        description=_(
            "Частично обновляет активную модель и/или активный промпт "
            "для текущего пользователя. "
            "Возможна только установка значений, входящих в список разрешённых."
        ),
        request=UserGptModelsSerializer,
        responses={200: UserModelsProfileResponseSerializer},
    )
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /api/ai/profile/
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # после обновления собираем полный ответ как в retrieve
        refreshed = self.get_object()
        data = self._build_profile_response_data(refreshed)
        return Response(data)

    @extend_schema(
        tags=["AI"],
        summary=_("Полностью обновить профиль моделей пользователя"),
        description=_(
            "Полностью обновляет активную модель и активный промпт "
            "для текущего пользователя."
        ),
        request=UserGptModelsSerializer,
        responses={200: UserModelsProfileResponseSerializer},
    )
    def update(self, request, *args, **kwargs):
        """
        PUT /api/ai/profile/
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        refreshed = self.get_object()
        data = self._build_profile_response_data(refreshed)
        return Response(data)


class GptModelPriceView(generics.RetrieveAPIView):
    """
    Возвращает стоимость входящих/исходящих токенов для выбранной модели.
    """

    queryset = GptModels.objects.all()
    serializer_class = GptModelPriceSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["AI"],
        summary=_("Получить цены модели"),
        description=_(
            "Возвращает стоимость входящих и исходящих токенов для указанной модели GPT."
        ),
        responses={200: GptModelPriceSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/ai/models/{id}/price/
        """
        return super().retrieve(request, *args, **kwargs)


class ClearHistoryView(APIView):
    """
    Сбрасывает окно истории запросов к ИИ для текущего пользователя.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["AI"],
        summary=_("Очистить историю запросов к ИИ"),
        description=_(
            "Обновляет поле 'time_start' для записи UserGptModels текущего пользователя, "
            "тем самым логически очищая историю запросов."
        ),
        request=None,
        responses={200: SimpleSuccessSerializer},
    )
    def post(self, request, *args, **kwargs):
        """
        POST /api/ai/history/clear/
        """
        UserGptModels.objects.update_or_create(
            user=request.user,
            defaults={"time_start": now()},
        )
        serializer = SimpleSuccessSerializer({"success": True})
        return Response(serializer.data, status=status.HTTP_200_OK)
