from __future__ import annotations

from typing import Any, Awaitable, Protocol

from asgiref.sync import async_to_sync
from django.conf import settings


class TaskiqTaskProto(Protocol):
    """
    Минимальный протокол для taskiq-задачи:
    - вызывается как async-функция;
    - имеет метод .kiq(...) для постановки в очередь.
    """

    def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[Any]:
        ...

    def kiq(self, *args: Any, **kwargs: Any) -> Awaitable[Any]:
        ...


async def run_task(
    task: TaskiqTaskProto,
    *args: Any,
    **kwargs: Any,
) -> Any | None:
    """
    В DEBUG:
        просто выполняет задачу локально: await task(*args, **kwargs)

    В проде:
        отправляет задачу в брокер: await task.kiq(*args, **kwargs)
        (результат не ждём, возвращаем None).

    Использование:
        await run_task(process_media_file_variants, media_file_id)
    """
    if getattr(settings, "DEBUG", False):
        return await task(*args, **kwargs)

    await task.kiq(*args, **kwargs)
    return None


async def run_task_fire_and_forget(
    task: TaskiqTaskProto,
    *args: Any,
    **kwargs: Any,
) -> Any | None:
    if getattr(settings, "DEBUG", False):
        await task(*args, **kwargs)
    else:
        await task.kiq(*args, **kwargs)


def run_task_sync(
    task: TaskiqTaskProto,
    *args: Any,
    **kwargs: Any,
) -> Any | None:
    """
    Синхронный вызов Taskiq-задачи.

    В DEBUG:
        выполняет задачу прямо здесь:
            async_to_sync(task)(...)

    В проде:
        отправляет в брокер:
            async_to_sync(task.kiq)(...)

    Возвращаемое значение:
        - в DEBUG: то, что вернёт задача;
        - в проде: обычно None (зависит от .kiq, но чаще всего результат не нужен).
    """
    if getattr(settings, "DEBUG", False):
        # Локально реально выполняем задачу
        return async_to_sync(task)(*args, **kwargs)

    # В проде — отправка в очередь
    return async_to_sync(task.kiq)(*args, **kwargs)
