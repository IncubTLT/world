from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.ai.models import (
    Consumer,
    GptModels,
    TextTransactions,
    UserGptModels,
    UserPrompt,
)


class TextTransactionSerializer(serializers.ModelSerializer):
    """Минимальное представление записи истории диалога с ИИ."""

    class Meta:
        model = TextTransactions
        fields = ("id", "question", "answer", "created_at")
        read_only_fields = fields


class AIHistoryResponseSerializer(serializers.Serializer):
    """
    Обёртка для ответа /api/ai/history/,
    чтобы схема совпадала с тем, что реально возвращается.
    """

    history = TextTransactionSerializer(
        many=True,
        read_only=True,
        help_text=_("Список последних запросов и ответов пользователя."),
    )


class GptModelPriceSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения цен модели."""

    class Meta:
        model = GptModels
        fields = ("id", "public_name", "title", "incoming_price", "outgoing_price", "consumer")
        read_only_fields = fields


class BalanceSerializer(serializers.Serializer):
    """Краткая информация о балансе пользователя."""

    remaining_balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text=_("Оставшийся баланс пользователя."),
    )


class UserGptModelsSerializer(serializers.ModelSerializer):
    """
    Настройки моделей для пользователя:
    - active_model — активная модель;
    - active_prompt — активный промпт;
    - approved_models — доступные модели (read-only).
    """

    active_model = serializers.PrimaryKeyRelatedField(
        queryset=GptModels.objects.all(),
        required=False,
        allow_null=True,
        help_text=_("Текущая активная модель для быстрого чата."),
    )
    active_prompt = serializers.PrimaryKeyRelatedField(
        queryset=UserPrompt.objects.all(),
        required=False,
        allow_null=True,
        help_text=_("Текущий активный промпт для быстрого чата."),
    )

    class Meta:
        model = UserGptModels
        fields = ("id", "active_model", "active_prompt", "approved_models", "time_start")
        read_only_fields = ("id", "approved_models", "time_start")

    def validate_active_model(self, value: GptModels | None) -> GptModels:
        """
        Поведение как в форме:
        - если модель не указана, подставляем дефолтную;
        - проверяем, что она входит в approved_models пользователя.
        """
        user_models: UserGptModels | None = self.instance

        if value is None:
            value = (
                GptModels.objects
                .filter(is_default=True, consumer=Consumer.FAST_CHAT)
                .first()
            )
            if value is None:
                raise serializers.ValidationError(
                    _("Активная модель не выбрана и отсутствует по умолчанию.")
                )

        if user_models and not user_models.approved_models.filter(pk=value.pk).exists():
            raise serializers.ValidationError(
                _("Эта модель не входит в список разрешённых для пользователя.")
            )

        return value

    def validate_active_prompt(self, value: UserPrompt | None) -> UserPrompt:
        """
        Аналогично форме:
        - если промпт не указан, подставляем дефолтный.
        """
        if value is None:
            value = (
                UserPrompt.objects
                .filter(is_default=True, consumer=Consumer.FAST_CHAT)
                .first()
            )
            if value is None:
                raise serializers.ValidationError(
                    _("Активный промпт не выбран и отсутствует по умолчанию.")
                )
        return value


class UserModelsProfileResponseSerializer(UserGptModelsSerializer):
    """
    Расширенный ответ профиля моделей пользователя.

    Это то, что фактически возвращает GET /api/ai/profile/:
    поля UserGptModels + список моделей с ценами + информация о балансе.
    """

    model_prices = GptModelPriceSerializer(
        many=True,
        read_only=True,
        help_text=_("Список моделей с ценами, доступных пользователю."),
    )
    balance = BalanceSerializer(
        read_only=True,
        required=False,
        help_text=_("Краткая информация о балансе пользователя."),
    )

    class Meta(UserGptModelsSerializer.Meta):
        # расширяем исходные поля базового сериализатора
        fields = UserGptModelsSerializer.Meta.fields + ("model_prices", "balance")
        read_only_fields = UserGptModelsSerializer.Meta.read_only_fields + (
            "model_prices",
            "balance",
        )


class SimpleSuccessSerializer(serializers.Serializer):
    """Простой ответ вида {'success': true}."""

    success = serializers.BooleanField(
        help_text=_("Признак успешного выполнения операции."),
    )
