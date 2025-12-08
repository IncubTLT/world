from __future__ import annotations

import random
from typing import Optional

from django.conf import settings
from redis import Redis


class CodeManager:
    """
    Менеджер одноразовых кодов на базе Redis (синхронная версия).

    Предполагается, что settings.REDIS_CLIENT — это экземпляр redis.Redis.
    """

    def __init__(self) -> None:
        self.redis: Redis = settings.REDIS_CLIENT

    def generate_code(self) -> str:
        """
        Генерация 6-значного кода.
        """
        return f"{random.randint(100000, 999999):06}"

    def set_code(self, key: str, code: str, expiry: int = 300) -> None:
        """
        Сохранение кода в Redis с указанием срока действия.

        :param key: Ключ Redis.
        :param code: Одноразовый код.
        :param expiry: Время жизни кода в секундах (по умолчанию 5 минут).
        """
        self.redis.set(key, code, ex=expiry)

    def get_code(self, key: str) -> Optional[str]:
        """
        Получение кода из Redis по ключу.

        :param key: Ключ Redis.
        :return: Код, если он существует, иначе None.
        """
        raw = self.redis.get(name=key)
        if raw is None:
            return None

        if isinstance(raw, (bytes, bytearray)):
            return raw.decode("utf-8")

        return str(raw)

    def delete_code(self, key: str) -> None:
        """
        Удаление кода из Redis по ключу.
        """
        self.redis.delete(key)

    def is_request_limited(
        self,
        ip_key: str,
        limit_seconds: int = 300,
        max_attempts: int = 1,
    ) -> bool:
        """
        Проверка ограничения по IP с учетом количества попыток.

        :param ip_key: Ключ для IP в Redis.
        :param limit_seconds: Время блокировки в секундах (по умолчанию 5 минут).
        :param max_attempts: Максимальное количество попыток (по умолчанию 1).
        :return: True, если ограничение активно, иначе False.
        """
        attempts = self.redis.incr(ip_key)

        if attempts > max_attempts:  # pyright: ignore[reportOperatorIssue]
            ttl = self.redis.ttl(ip_key)
            # ttl:
            #  -1 — нет времени жизни
            #  -2 — ключ не существует
            if ttl == -1:
                self.redis.expire(ip_key, limit_seconds)
            return True

        if attempts == 1:
            self.redis.expire(ip_key, limit_seconds)

        return False

    def verify_code(self, key: str, code: str) -> bool:
        """
        Проверка правильности одноразового кода.

        :param key: Ключ Redis.
        :param code: Проверяемый код.
        :return: True, если код совпадает, иначе False.
        """
        stored_code = self.get_code(key)
        if stored_code and stored_code == code:
            self.delete_code(key)
            return True
        return False
