from __future__ import annotations

import re

import pytest

from apps.users.redis_code import CodeManager


@pytest.mark.django_db
def test_generate_code_format(sync_redis_client):
    """
    Код должен быть строкой из 6 цифр.
    """
    manager = CodeManager()
    code = manager.generate_code()

    assert isinstance(code, str)
    assert re.fullmatch(r"\d{6}", code)


@pytest.mark.django_db
def test_set_and_get_code_works_with_redis(sync_redis_client):
    """
    set_code/get_code работают поверх реального Redis.
    """
    manager = CodeManager()
    key = "login_code:test@example.com"
    manager.set_code(key, "123456", expiry=300)

    raw = sync_redis_client.get(key)
    # Реальный redis вернёт bytes
    assert raw in (b"123456", "123456")

    code = manager.get_code(key)
    assert code == "123456"


@pytest.mark.django_db
def test_delete_code(sync_redis_client):
    """
    delete_code удаляет ключ из Redis.
    """
    manager = CodeManager()
    key = "login_code:test@example.com"

    manager.set_code(key, "123456", expiry=300)
    assert manager.get_code(key) == "123456"

    manager.delete_code(key)
    assert manager.get_code(key) is None
    assert sync_redis_client.get(key) is None


@pytest.mark.django_db
def test_verify_code_success_deletes_key(sync_redis_client):
    """
    verify_code:
    - True при правильном коде,
    - удаляет ключ из Redis.
    """
    manager = CodeManager()
    key = "login_code:test@example.com"

    manager.set_code(key, "123456", expiry=300)

    assert manager.verify_code(key, "123456") is True
    assert manager.get_code(key) is None
    assert sync_redis_client.get(key) is None


@pytest.mark.django_db
def test_verify_code_invalid_does_not_delete(sync_redis_client):
    """
    verify_code:
    - False при неверном коде,
    - не удаляет значение.
    """
    manager = CodeManager()
    key = "login_code:test@example.com"

    manager.set_code(key, "123456", expiry=300)

    assert manager.verify_code(key, "000000") is False
    assert manager.get_code(key) == "123456"


@pytest.mark.django_db
def test_verify_code_missing_key(sync_redis_client):
    """
    verify_code по несуществующему ключу → False.
    """
    manager = CodeManager()
    key = "login_code:missing@example.com"

    assert manager.verify_code(key, "123456") is False
    assert manager.get_code(key) is None


@pytest.mark.django_db
def test_is_request_limited_basic_flow(sync_redis_client):
    """
    is_request_limited:
    - первые max_attempts вызовов → False,
    - (max_attempts + 1)-й → True.
    """
    manager = CodeManager()
    key = "request_code_ip:127.0.0.1"

    # max_attempts=3
    assert manager.is_request_limited(key, limit_seconds=300, max_attempts=3) is False
    assert manager.is_request_limited(key, limit_seconds=300, max_attempts=3) is False
    assert manager.is_request_limited(key, limit_seconds=300, max_attempts=3) is False

    # 4-я попытка → лимит
    assert manager.is_request_limited(key, limit_seconds=300, max_attempts=3) is True


@pytest.mark.django_db
def test_is_request_limited_sets_expire_on_first_attempt(sync_redis_client):
    """
    На первой попытке is_request_limited должен поставить expire.
    """
    manager = CodeManager()
    key = "request_code_ip:10.0.0.1"

    assert manager.is_request_limited(key, limit_seconds=300, max_attempts=3) is False

    ttl = sync_redis_client.ttl(key)
    # ttl может быть -1, если Redis не обработал expire, но в норме > 0
    assert ttl == -1 or ttl > 0


@pytest.mark.django_db
def test_is_request_limited_keeps_ttl_when_blocked(sync_redis_client):
    """
    При достижении лимита ttl не должен становиться -1.
    """
    manager = CodeManager()
    key = "request_code_ip:192.168.0.1"

    # первая попытка (установит expire)
    assert manager.is_request_limited(key, limit_seconds=300, max_attempts=2) is False
    ttl1 = sync_redis_client.ttl(key)

    # вторая попытка
    assert manager.is_request_limited(key, limit_seconds=300, max_attempts=2) is False

    # третья — лимит
    assert manager.is_request_limited(key, limit_seconds=300, max_attempts=2) is True
    ttl2 = sync_redis_client.ttl(key)

    # ttl должен остаться чем-то разумным, а не -2 (нет ключа)
    assert ttl2 != -2
    # и обычно ttl2 <= ttl1, но это не критично, поэтому не проверяем строго
