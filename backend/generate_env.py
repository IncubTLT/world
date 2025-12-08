#!/usr/bin/env python3
import secrets
import string
from cryptography.fernet import Fernet


def generate_secret_key(length: int = 50) -> str:
    """
    Генерирует SECRET_KEY в стиле Django:
    50 символов из безопасного набора.
    Подходит для .env и настроек Django.
    """
    chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
    return f"django-insecure-{''.join(secrets.choice(chars) for _ in range(length))}"


def generate_salt_key() -> str:
    """
    Генерирует fernet-ключ (base64, 32 байта), чтобы использовать его как SALT_KEY.
    """
    return Fernet.generate_key().decode()


def generate_cert_passphrase(length: int = 32) -> str:
    """
    Генерирует случайную парольную фразу URL-safe, чтобы использовать как CERT_PASSPHRASE.
    По умолчанию 32 байта (≈43 символа).
    """
    return secrets.token_urlsafe(length)


def generate_redis_password(length: int = 32) -> str:
    """
    Генерирует пароль для Redis из [a-zA-Z0-9].
    Без спецсимволов: безопасно для redis.conf, URL-подключения и .env.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_db_password(length: int = 32) -> str:
    """
    Генерирует пароль для БД.
    Используем [a-zA-Z0-9], чтобы не ловить проблемы в URL-подключениях.
    При желании можно расширить алфавит.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_env_keys() -> dict[str, str]:
    """
    Генерирует все нужные ключи и возвращает словарь вида:
    {
        "DJANGO_SECRET_KEY": "...",
        "SALT_KEY": "...",
        "CERT_PASSPHRASE": "...",
        "REDIS_PASSWORD": "...",
        "POSTGRES_PASSWORD": "...",
    }
    """
    return {
        "DJANGO_SECRET_KEY": generate_secret_key(),
        "SALT_KEY": generate_salt_key(),
        "CERT_PASSPHRASE": generate_cert_passphrase(),
        "REDIS_PASSWORD": generate_redis_password(),
        "POSTGRES_PASSWORD": generate_db_password(),
    }


def main() -> None:
    env_vars = generate_env_keys()
    print("# Скопируйте эти строки в ваш .env:")
    for key, value in env_vars.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
