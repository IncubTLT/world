from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.redis_code import CodeManager

User = get_user_model()


@pytest.mark.django_db
def test_request_code_success(api_client, sync_redis_client, monkeypatch):
    """
    Успешный запрос кода:
    - 200 OK
    - код сохранён в Redis (нижний регистр email)
    - send_activation_email вызван с тем же кодом.
    """
    from apps.users import views as auth_views

    sent_emails: list[dict[str, Any]] = []

    def fake_send_activation_email(*, email: str, code: str) -> None:
        sent_emails.append({"email": email, "code": code})

    monkeypatch.setattr(auth_views, "send_activation_email", fake_send_activation_email)

    url = reverse("auth-request-code")
    payload = {"email": "TestUser@Example.COM"}

    response = api_client.post(url, payload, format="json", REMOTE_ADDR="1.2.3.4")

    assert response.status_code == 200
    assert "Код отправлен" in response.data["detail"]

    key = "login_code:testuser@example.com"
    stored = sync_redis_client.get(key)
    assert stored is not None

    # Проверяем "отправленное письмо"
    assert len(sent_emails) == 1
    assert sent_emails[0]["email"] == "testuser@example.com"
    assert str(sent_emails[0]["code"]) == (
        stored.decode("utf-8") if isinstance(stored, (bytes, bytearray)) else str(stored)
    )


@pytest.mark.django_db
def test_request_code_invalid_payload(api_client, sync_redis_client):
    """
    Пустые данные / отсутствие email → 400.
    """
    url = reverse("auth-request-code")

    response = api_client.post(url, {}, format="json")
    assert response.status_code == 400
    assert "email" in response.data


@pytest.mark.django_db
def test_request_code_rate_limit_by_ip(api_client, sync_redis_client, monkeypatch):
    """
    Превышение лимита запросов кода по IP → 429.
    """
    from apps.users import views as auth_views

    monkeypatch.setattr(auth_views, "send_activation_email", lambda *args, **kwargs: None)

    url = reverse("auth-request-code")
    payload = {"email": "user@example.com"}

    # max_attempts=3 → первые 3 раз — 200, 4-й — 429
    for i in range(3):
        resp = api_client.post(url, payload, format="json", REMOTE_ADDR="5.6.7.8")
        assert resp.status_code == 200

    resp4 = api_client.post(url, payload, format="json", REMOTE_ADDR="5.6.7.8")
    assert resp4.status_code == 429
    assert "Повторный запрос кода" in resp4.data["detail"]


@pytest.mark.django_db
def test_verify_code_success_creates_user_and_returns_tokens(api_client, sync_redis_client):
    """
    Успешная верификация:
    - пользователь создаётся,
    - email_confirmed=True,
    - есть access/refresh,
    - в access есть claim email.
    """
    email = "newuser@example.com"
    key = f"login_code:{email}"

    manager = CodeManager()
    manager.set_code(key, "123456", expiry=300)

    url = reverse("auth-verify-code")
    payload = {"email": email, "code": "123456"}

    response = api_client.post(url, payload, format="json", REMOTE_ADDR="10.0.0.1")

    assert response.status_code == 200

    data = response.data
    assert "access" in data
    assert "refresh" in data
    assert "user" in data

    user_data = data["user"]
    assert user_data["email"] == email

    user = User.objects.get(email=email)
    assert getattr(user, "email_confirmed", False) is True

    # Проверяем, что в access-токене есть нужные клеймы
    token = AccessToken(data["access"])
    assert token["email"] == email
    assert token.get("display_name") == user.display_name or user.email


@pytest.mark.django_db
def test_verify_code_existing_user_email_confirmed_toggle(api_client, sync_redis_client):
    """
    Если пользователь уже существует с email_confirmed=False,
    verify-code должен выставить email_confirmed=True и не создавать дубликат.
    """
    email = "existing@example.com"
    user = User.objects.create(
        email=email,
        display_name="Existing",
        email_confirmed=False,
    )
    key = f"login_code:{email}"

    manager = CodeManager()
    manager.set_code(key, "123456", expiry=300)

    url = reverse("auth-verify-code")
    payload = {"email": email, "code": "123456"}

    response = api_client.post(url, payload, format="json", REMOTE_ADDR="11.11.11.11")

    assert response.status_code == 200

    user.refresh_from_db()
    assert user.email_confirmed is True
    # Убедимся, что не появился второй пользователь
    assert User.objects.filter(email=email).count() == 1


@pytest.mark.django_db
def test_verify_code_invalid_code(api_client, sync_redis_client):
    """
    Неверный код → 400 + code=invalid_code.
    """
    email = "user2@example.com"
    key = f"login_code:{email}"

    manager = CodeManager()
    manager.set_code(key, "123456", expiry=300)

    url = reverse("auth-verify-code")
    payload = {"email": email, "code": "000000"}

    response = api_client.post(url, payload, format="json", REMOTE_ADDR="12.12.12.12")

    assert response.status_code == 400
    assert response.data["code"] == "invalid_code"
    assert "Неверный или истёкший код" in response.data["detail"]

    # Код при этом не должен удаляться
    assert manager.get_code(key) == "123456"


@pytest.mark.django_db
def test_verify_code_missing_redis_code(api_client, sync_redis_client):
    """
    Код в Redis отсутствует (истёк или не создавался) → 400 invalid_code.
    """
    email = "user-missing@example.com"
    key = f"login_code:{email}"
    # Ничего не ставим в Redis

    url = reverse("auth-verify-code")
    payload = {"email": email, "code": "123456"}

    response = api_client.post(url, payload, format="json", REMOTE_ADDR="13.13.13.13")

    assert response.status_code == 400
    assert response.data["code"] == "invalid_code"


@pytest.mark.django_db
def test_verify_code_too_many_attempts(api_client, sync_redis_client):
    """
    Превышение лимита попыток ввода кода → 429 + code=too_many_attempts.
    """
    email = "user3@example.com"
    url = reverse("auth-verify-code")
    payload = {"email": email, "code": "000000"}

    # Никакого кода в Redis не задаём

    # max_attempts=5 → первые 5 раз is_request_limited=False (ошибка будет invalid_code),
    # на 6-й раз is_request_limited=True → 429.
    statuses: list[int] = []
    for i in range(5):
        resp = api_client.post(url, payload, format="json", REMOTE_ADDR="14.14.14.14")
        statuses.append(resp.status_code)
        # Должно быть 400 invalid_code
        assert resp.status_code == 400
        assert resp.data["code"] == "invalid_code"

    resp6 = api_client.post(url, payload, format="json", REMOTE_ADDR="14.14.14.14")
    assert resp6.status_code == 429
    assert resp6.data["code"] == "too_many_attempts"
    assert "Превышен лимит попыток" in resp6.data["detail"]
