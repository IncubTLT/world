from __future__ import annotations

from ipaddress import ip_address
from typing import Any, Mapping, Optional, Sequence, Tuple

from django.http import HttpRequest
from rest_framework.request import Request


def _clean_ip_token(s: str | None) -> Optional[str]:
    """
    Нормализует IP-строку:
    - убирает кавычки/скобки (RFC 7239: for="[2001:db8::1]")
    - отбрасывает порт (IPv4:port или [IPv6]:port)
    - игнорирует 'unknown' и мусор.
    Возвращает корректный IP или None.
    """
    if not s:
        return None

    s = s.strip().strip('"').strip("'")
    if s.lower() == "unknown":
        return None

    # Вариант [IPv6]:port или [IPv6]
    if s.startswith("["):
        end = s.find("]")
        if end > 0:
            s = s[1:end]

    # Вариант IPv4:port — оставляем только адрес (не ломаем IPv6)
    if ":" in s and s.count(":") == 1 and "." in s.split(":", 1)[0]:
        s = s.split(":", 1)[0]

    try:
        ip_address(s)
        return s
    except ValueError:
        return None


def get_client_ip(request: HttpRequest | Request) -> Optional[str]:
    """
    Получить IP клиента из HTTP/DRF-запроса.

    Приоритет заголовков:
      1) X-Forwarded-For — берём ПЕРВЫЙ валидный IP (левый край).
      2) Forwarded (RFC 7239): for=...
      3) X-Real-IP
      4) REMOTE_ADDR

    Возвращает строку IP или None, если всё плохо.
    """
    # DRF Request имеет .headers, HttpRequest — нет, но у обоих есть .META.
    headers = getattr(request, "headers", None)
    if headers is None:
        # fallback для "голого" HttpRequest
        def h_get(name: str, default: str = "") -> str:
            meta_key = f"HTTP_{name.upper().replace('-', '_')}"
            return request.META.get(meta_key, default)
    else:
        h_get = headers.get  # type: ignore[assignment]

    # 1) X-Forwarded-For: client, proxy1, proxy2
    xff = h_get("X-Forwarded-For", "")
    if xff:
        for part in xff.split(","):
            ip = _clean_ip_token(part)
            if ip:
                return ip

    # 2) Forwarded: for=...;proto=..., for=...
    fwd = h_get("Forwarded", "")
    if fwd:
        for item in fwd.split(","):
            for token in item.split(";"):
                token = token.strip()
                if token.lower().startswith("for="):
                    ip = _clean_ip_token(token[4:].strip())
                    if ip:
                        return ip

    # 3) X-Real-IP
    ip = _clean_ip_token(h_get("X-Real-IP", ""))
    if ip:
        return ip

    # 4) REMOTE_ADDR из META
    return _clean_ip_token(request.META.get("REMOTE_ADDR", ""))


def get_client_ip_from_scope(scope: Mapping[str, Any]) -> Optional[str]:
    """
    Получить IP клиента из ASGI scope (Channels, ASGI-приложение и т.п.).

    Тоже учитывает X-Forwarded-For, затем client-адрес.
    """
    headers_raw: Sequence[Tuple[bytes, bytes]] = scope.get("headers", [])  # type: ignore[assignment]
    headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in headers_raw}

    x_forwarded_for = headers.get("x-forwarded-for")
    if x_forwarded_for:
        # X-Forwarded-For: client, proxy1, proxy2
        for part in x_forwarded_for.split(","):
            ip = _clean_ip_token(part)
            if ip:
                return ip

    client = scope.get("client")
    if isinstance(client, (list, tuple)) and client:
        return _clean_ip_token(str(client[0]))

    return None


def get_ref_url(request: HttpRequest | Request) -> Optional[str]:
    """
    Получить URL, с которого пришёл запрос (Referer).

    Возвращает строку с URL или None.
    Ничего дополнительно не кодирует — фронт при необходимости сам решит, как его использовать.
    """
    headers = getattr(request, "headers", None)
    if headers is not None:
        ref = headers.get("Referer")
        if ref:
            return ref

    # fallback для голого HttpRequest
    return request.META.get("HTTP_REFERER")
