"""Gunicorn *production* config file"""
import multiprocessing

from uvicorn_worker import UvicornWorker


class CustomUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        "http": "httptools",    # Использовать httptools для HTTP/1.1
        # "lifespan": "on",       # Поддержка lifespan событий
        "log_level": "info",
        "timeout_keep_alive": 600,
    }


# Получение количества ядер CPU
cores = multiprocessing.cpu_count()
# Django ASGI application path in pattern MODULE_NAME:VARIABLE_NAME
asgi_app = "asgi:application"
# Уровень логирования
loglevel = "debug"
# Количество воркеров, рекомендуется 2n+1
workers = 1
# Адрес и порт для привязки
bind = '0.0.0.0:8000'
# Класс воркера Uvicorn
worker_class = "config.entrypoints.server.dev.CustomUvicornWorker"
# Отключение автоматической перезагрузки кода
reload = True
timeout = 600
graceful_timeout = 600
keepalive = 600
