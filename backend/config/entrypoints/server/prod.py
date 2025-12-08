from uvicorn_worker import UvicornWorker

"""Gunicorn *production* config file"""


class CustomUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        "http": "httptools",    # Использовать httptools для HTTP/1.1
        "lifespan": "on",       # Поддержка lifespan событий
        "log_level": "info",    # Уровень логов
    }


# Django ASGI application path in pattern MODULE_NAME:VARIABLE_NAME
asgi_app = "asgi:application"
# Уровень логирования
loglevel = "info"
# Количество воркеров, рекомендуется 2n+1
workers = 2
# Адрес и порт для привязки
bind = '0.0.0.0:8000'
# Класс воркера Uvicorn
worker_class = "config.entrypoints.server.dev.CustomUvicornWorker"
# Отключение автоматической перезагрузки кода
reload = False
