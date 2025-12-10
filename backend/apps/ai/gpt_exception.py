import traceback


class LogTracebackExceptionError(Exception):
    """Абстракция для логирования traceback."""
    def __init__(self, message, log_traceback=True):
        super().__init__(message)
        self.log_traceback = log_traceback


class InWorkError(LogTracebackExceptionError):
    """Исключение, вызываемое, если запрос находится в работе."""
    pass


class LongQueryError(LogTracebackExceptionError):
    """Исключение для случаев, когда текст запроса слишком большой."""
    def __init__(self, message="Слишком большой текст запроса. Попробуйте сформулировать его короче."):
        self.message = message
        super().__init__(self.message, log_traceback=False)


class LowTokensBalanceError(LogTracebackExceptionError):
    """Недостаточно токенов."""
    def __init__(self, message="Недостаточно средств. Вы исчерпали свой лимит."):
        self.message = message
        super().__init__(self.message, log_traceback=False)


class UnhandledError(LogTracebackExceptionError):
    """Исключение для обработки неожиданных ошибок."""
    pass


class OpenAIRequestError(LogTracebackExceptionError):
    """Ошибки, связанные с запросами к OpenAI."""
    pass


class OpenAIResponseError(OpenAIRequestError):
    """Ошибки, связанные с ответами от OpenAI."""
    pass


class OpenAIConnectionError(OpenAIRequestError):
    """Ошибки соединения при запросах к OpenAI."""
    pass


class OpenAIJSONDecodeError(OpenAIRequestError):
    """Ошибки при десериализации ответов OpenAI."""
    pass


class ValueChoicesError(OpenAIRequestError):
    """Ошибки в содержании ответа."""
    pass


def format_exception_message(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"


async def handle_exceptions(err: Exception, include_traceback: bool = False) -> tuple[str, Exception, str]:
    user_error_text = 'Что-то пошло не так 🤷🏼'

    error_messages = {
        InWorkError: "⏳ Уже работаю над вашим вопросом — ответ скоро будет.",
        LongQueryError: "📏 Запрос слишком длинный. Сократите до одного вопроса или 3–5 тезисов.",
        LowTokensBalanceError: "💳 Недостаточно средств. Пополните баланс или отправьте запрос без веб-поиска.",
        ValueChoicesError: "🤔 Ответ вышел слишком расплывчатым. Уточните цель и критерии — попробуем иначе.",
        OpenAIResponseError: "🧠 Не удалось сформировать ответ. Перефразируйте запрос или попробуйте позже.",
        OpenAIConnectionError: "📡 Нет связи с сервером ИИ. Проверьте интернет/прокси и повторите попытку.",
        OpenAIJSONDecodeError: "🧩 Ошибка при обработке ответа. Повторите запрос — я попробую другим способом.",
        UnhandledError: "❗️ Непредвиденная ошибка. Мы уже разбираемся. Повторите попытку чуть позже.",
    }

    user_msg = error_messages.get(type(err), user_error_text)

    trace_log = ''
    if include_traceback or getattr(err, 'log_traceback', False):
        trace_log = (
            "📋 **Трассировка ошибки**:\n"
            "```python\n"
            + ''.join(traceback.format_exception(type(err), err, err.__traceback__)).strip()
            + "\n```"
        )

    err.__cause__ = None
    err.__context__ = None

    return user_msg, err, trace_log
