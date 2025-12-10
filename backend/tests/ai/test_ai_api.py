from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APIClient

from apps.ai.models import Consumer, GptModels, TextTransactions, UserGptModels, UserPrompt


User = get_user_model()


@pytest.mark.django_db
def test_ai_history_filters_by_user_consumer_and_answer(
    api_client: APIClient,
    regular_user: User,
):
    """
    История:
    - возвращает только записи текущего пользователя,
    - только consumer=FAST_CHAT,
    - только с непустым answer.
    """
    other_user = User.objects.create_user(
        email="other@example.com",
    )

    # Подходящая запись: наш user, FAST_CHAT, непустой ответ
    valid = TextTransactions.objects.create(
        user=regular_user,
        question="Q-valid",
        answer="A-valid",
        consumer=Consumer.FAST_CHAT,
    )
    # Неподходящая: пустой ответ
    TextTransactions.objects.create(
        user=regular_user,
        question="Q-empty",
        answer="",
        consumer=Consumer.FAST_CHAT,
    )
    # Неподходящая: другой consumer
    TextTransactions.objects.create(
        user=regular_user,
        question="Q-reminder",
        answer="A-reminder",
        consumer=Consumer.REMINDER,
    )
    # Неподходящая: другой пользователь
    TextTransactions.objects.create(
        user=other_user,
        question="Q-other",
        answer="A-other",
        consumer=Consumer.FAST_CHAT,
    )

    api_client.force_authenticate(user=regular_user)
    url = reverse("ai:history")

    resp = api_client.get(url)

    assert resp.status_code == status.HTTP_200_OK
    history = resp.data["history"]

    assert len(history) == 1
    assert history[0]["question"] == valid.question
    assert history[0]["answer"] == valid.answer


@pytest.mark.django_db
def test_ai_history_limits_to_20_and_sorted(
    api_client: APIClient,
    regular_user: User,
):
    """
    История:
    - возвращает не больше 20 записей,
    - мы их отдаём в хронологическом порядке (от старых к новым).
    """
    base = now()

    # Создаём 25 записей с разным created_at
    for i in range(25):
        tx = TextTransactions.objects.create(
            user=regular_user,
            question=f"Q{i}",
            answer=f"A{i}",
            consumer=Consumer.FAST_CHAT,
        )
        # Явно раскладываем по времени, чтобы порядок был детерминированным
        TextTransactions.objects.filter(pk=tx.pk).update(
            created_at=base + timedelta(minutes=i),
        )

    api_client.force_authenticate(user=regular_user)
    url = reverse("ai:history")

    resp = api_client.get(url)

    assert resp.status_code == status.HTTP_200_OK
    history = resp.data["history"]

    # Ограничение в 20 штук
    assert len(history) == 20

    questions = [item["question"] for item in history]
    # Ожидаем Q5..Q24 (самые свежие 20, но мы их разворачиваем от старых к новым)
    assert questions[0] == "Q5"
    assert questions[-1] == "Q24"


@pytest.mark.django_db
def test_ai_history_requires_authentication(api_client: APIClient):
    """
    Неаутентифицированный пользователь не получает историю.
    """
    url = reverse("ai:history")
    resp = api_client.get(url)

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# --- Профиль моделей пользователя ---


def _create_default_prompt() -> UserPrompt:
    """
    Вспомогательная функция: создаёт дефолтный промпт.
    Гарантирует выполнение clean() (должен быть хотя бы один is_default=True).
    """
    return UserPrompt.objects.create(
        title="Default prompt",
        prompt_text="Default prompt text",
        ru_prompt_text="Дефолтный текст промпта",
        is_default=True,
        consumer=Consumer.FAST_CHAT,
    )


def _create_gpt_model(
    *,
    public_name: str,
    title: str,
    is_default: bool = False,
    is_free: bool = False,
    incoming_price: Decimal | int = 0,
    outgoing_price: Decimal | int = 0,
    consumer: str = Consumer.FAST_CHAT,
) -> GptModels:
    """
    Вспомогательная фабрика для GptModels, чтобы не копировать поля в тестах.
    """
    return GptModels.objects.create(
        public_name=public_name,
        title=title,
        token="test-token",
        context_window=8192,
        max_request_token=4096,
        is_default=is_default,
        is_free=is_free,
        incoming_price=incoming_price,
        outgoing_price=outgoing_price,
        consumer=consumer,
    )


@pytest.mark.django_db
def test_profile_retrieve_creates_user_models_and_sets_approved_free_models(
    api_client: APIClient,
    regular_user: User,
):
    """
    GET /api/ai/profile/:
    - создаёт UserGptModels, если его ещё нет;
    - выставляет active_model/active_prompt по умолчанию;
    - approved_models содержит только бесплатные FAST_CHAT-модели,
      если у пользователя нет положительного баланса.
    """
    default_prompt = _create_default_prompt()

    default_model = _create_gpt_model(
        public_name="Default GPT",
        title="gpt-default",
        is_default=True,
        is_free=True,
        incoming_price=Decimal("0.10"),
        outgoing_price=Decimal("0.20"),
        consumer=Consumer.FAST_CHAT,
    )
    free_model_2 = _create_gpt_model(
        public_name="Free GPT 2",
        title="gpt-free-2",
        is_default=False,
        is_free=True,
        incoming_price=0,
        outgoing_price=0,
        consumer=Consumer.FAST_CHAT,
    )
    paid_model = _create_gpt_model(
        public_name="Paid GPT",
        title="gpt-paid",
        is_default=False,
        is_free=False,
        incoming_price=Decimal("1.00"),
        outgoing_price=Decimal("2.00"),
        consumer=Consumer.FAST_CHAT,
    )
    image_model = _create_gpt_model(
        public_name="Image GPT",
        title="gpt-image",
        is_default=False,
        is_free=True,
        incoming_price=Decimal("0.50"),
        outgoing_price=Decimal("0.50"),
        consumer=Consumer.IMAGE,
    )

    api_client.force_authenticate(user=regular_user)
    url = reverse("ai:profile")

    resp = api_client.get(url)

    assert resp.status_code == status.HTTP_200_OK

    data = resp.data

    # Проверяем, что объект профиля вообще создался
    user_models = UserGptModels.objects.get(user=regular_user)

    # active_model и active_prompt должны быть выставлены в дефолтные
    assert data["active_model"] == default_model.id
    assert data["active_prompt"] == default_prompt.id
    assert user_models.active_model_id == default_model.id
    assert user_models.active_prompt_id == default_prompt.id

    # approved_models — только бесплатные FAST_CHAT-модели
    approved_ids = set(data["approved_models"])
    assert default_model.id in approved_ids
    assert free_model_2.id in approved_ids
    assert paid_model.id not in approved_ids
    # IMAGE-модель не входит в approved_models (там только FAST_CHAT)
    assert image_model.id not in approved_ids

    # Дополнительно: баланс и model_prices присутствуют в ответе
    assert "balance" in data
    assert "model_prices" in data
    assert isinstance(data["model_prices"], list)


@pytest.mark.django_db
def test_profile_partial_update_changes_active_model_and_prompt(
    api_client: APIClient,
    regular_user: User,
):
    """
    PATCH /api/ai/profile/:
    - позволяет сменить active_model и active_prompt
      на значения из approved_models/существующих промптов.
    """
    default_prompt = _create_default_prompt()
    alt_prompt = UserPrompt.objects.create(
        title="Alt prompt",
        prompt_text="Alt prompt text",
        ru_prompt_text="Альтернативный текст промпта",
        is_default=False,
        consumer=Consumer.FAST_CHAT,
    )

    default_model = _create_gpt_model(
        public_name="Default GPT",
        title="gpt-default",
        is_default=True,
        is_free=True,
        incoming_price=0,
        outgoing_price=0,
        consumer=Consumer.FAST_CHAT,
    )
    alt_model = _create_gpt_model(
        public_name="Alt GPT",
        title="gpt-alt",
        is_default=False,
        is_free=True,  # важно: иначе не попадёт в approved_models
        incoming_price=0,
        outgoing_price=0,
        consumer=Consumer.FAST_CHAT,
    )

    api_client.force_authenticate(user=regular_user)

    # Первый вызов создаёт профиль и approved_models
    profile_url = reverse("ai:profile")
    resp_initial = api_client.get(profile_url)
    assert resp_initial.status_code == status.HTTP_200_OK

    payload = {
        "active_model": alt_model.id,
        "active_prompt": alt_prompt.id,
    }

    resp = api_client.patch(profile_url, payload, format="json")

    assert resp.status_code == status.HTTP_200_OK
    data = resp.data

    assert data["active_model"] == alt_model.id
    assert data["active_prompt"] == alt_prompt.id

    user_models = UserGptModels.objects.get(user=regular_user)
    assert user_models.active_model_id == alt_model.id
    assert user_models.active_prompt_id == alt_prompt.id

    # Проверяем, что approved_models содержит alt_model (иначе валидация бы упала)
    assert alt_model.id in set(user_models.approved_models.values_list("id", flat=True))


# --- Очистка истории ---


@pytest.mark.django_db
def test_clear_history_updates_time_start(
    api_client: APIClient,
    regular_user: User,
):
    """
    POST /api/ai/history/clear/:
    - создаёт или обновляет UserGptModels,
    - time_start устанавливается в "сейчас".
    """
    api_client.force_authenticate(user=regular_user)
    url = reverse("ai:history-clear")

    before = now()
    resp = api_client.post(url)
    after = now()

    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["success"] is True

    user_models = UserGptModels.objects.get(user=regular_user)

    assert user_models.time_start is not None
    assert before <= user_models.time_start <= after


# --- Цена модели ---


@pytest.mark.django_db
def test_model_price_returns_correct_data(api_client: APIClient):
    """
    GET /api/ai/models/{id}/price/:
    - отдаёт цены входящих/исходящих токенов и базовую информацию о модели.
    """
    model = _create_gpt_model(
        public_name="Price GPT",
        title="gpt-price",
        is_default=True,
        is_free=False,
        incoming_price=Decimal("1.23"),
        outgoing_price=Decimal("4.56"),
        consumer=Consumer.FAST_CHAT,
    )

    url = reverse("ai:model-price", kwargs={"pk": model.pk})

    resp = api_client.get(url)

    assert resp.status_code == status.HTTP_200_OK

    data = resp.data
    assert data["id"] == model.id
    assert data["public_name"] == model.public_name
    assert data["title"] == model.title

    # Decimal приводим к строке, т.к. DRF по умолчанию сериализует Decimal -> string
    assert str(data["incoming_price"]) == str(model.incoming_price)
    assert str(data["outgoing_price"]) == str(model.outgoing_price)
    assert data["consumer"] == model.consumer
