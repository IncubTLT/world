from __future__ import annotations

from typing import Generator

import pytest
from django.conf import settings
from rest_framework.test import APIClient


@pytest.fixture
def sync_redis_client() -> Generator:
    """
    Фикстура для реального Redis (settings.REDIS_CLIENT).

    - проверяем доступность redis (ping),
    - чистим БД перед тестом,
    - после теста ещё раз чистим на всякий.
    """
    client = settings.REDIS_CLIENT
    try:
        client.ping()
    except Exception as exc:  # pragma: no cover - зависит от окружения
        pytest.skip(f"Redis недоступен: {exc!r}")

    client.flushdb()
    try:
        yield client
    finally:
        client.flushdb()


@pytest.fixture
def api_client() -> APIClient:
    """
    DRF APIClient для запросов к endpoint’ам.
    """
    return APIClient()
