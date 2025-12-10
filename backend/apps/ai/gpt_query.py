import asyncio
import json
import logging
import pprint
import re
from datetime import timedelta
from decimal import Decimal
from typing import Set

import anthropic
import httpx
import markdown
import openai
import tiktoken_async
from apps.utils.re_compile import PUNCTUATION_RE, normalize_text
from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup
from config.async_redis import AsyncRedisClient
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Model
from django.utils.timezone import now
from httpx_socks import AsyncProxyTransport

from .gpt_exception import (InWorkError, LongQueryError, LowTokensBalanceError,
                            OpenAIConnectionError, OpenAIResponseError,
                            UnhandledError, ValueChoicesError,
                            handle_exceptions)
from .mock_text_generator import client_mock, text_stream_generator
from .models import GptModels, ProviderCDK, UserGptModels

User = get_user_model()
logger = logging.getLogger(__name__)


class GetAnswerGPT():
    """
    Класс для получения ответов от модели GPT.

    """
    MAX_TYPING_TIME = 3
    EXCLUDED_CREATIVITY_MODELS = {"o1", "reasoner", "o3", "o4", "gpt-5"}

    def __init__(
        self, query_text: str, user: 'Model', history_model: 'Model', chat_id: int = None,
        creativity_controls: dict = {}, consumer: str = 'FCH', image_url: str = None, stream: bool = False
    ) -> None:
        # Инициализация свойств класса
        self.user = user                    # модель пользователя пославшего запрос
        self.history_model = history_model  # модель для хранения истории
        self.query_text = query_text        # текст запроса пользователя
        self.query_text_tokens = None       # количество токенов в запросе
        self.chat_id = chat_id              # id чата
        self.creativity_controls = creativity_controls      # параметры которые контролируют креативность и разнообразие текста
        # Дополнительные свойства
        self.assist_prompt_tokens = 0       # количество токенов в промпте ассистента в head модели
        self.all_prompt = []                # общий промпт для запроса
        self.current_time = now()           # текущее время для окна истории
        self.return_text = ''               # текст полученный в ответе от модели
        self.return_text_tokens = None      # количество токенов в ответе
        self.user_models = None             # разрешенные GPT модели пользователя
        self.consumer = consumer            # потребитель запроса для истории
        self.reply_to_message_text = None   # текст в случает запроса на ответ GPT
        self.image_url = image_url          # url картинки, если передается к запросу
        self.stream = stream
        self.redis_client = AsyncRedisClient.get_client()

    @staticmethod
    def clean_and_split_text(text: str, word_limit=15) -> Set:
        """
        Функция для удаления HTML и Markdown разметки и очистки текста от знаков препинания.
        Возвращает множество по умолчанию до 15 первых уникальных слов.
        """
        html_text = markdown.markdown(text)
        soup = BeautifulSoup(html_text, "html.parser")
        clean_text = soup.get_text()

        clean_text = PUNCTUATION_RE.sub('', clean_text)
        words = clean_text.split()

        return set(words[:word_limit])

    @property
    def check_long_query(self) -> bool:
        return self.query_text_tokens > self.model.max_request_token

    @property
    def assist_prompt(self):
        return 'Your name is Eva.'

    async def get_answer_chat_gpt(self) -> dict:
        """Основная логика."""
        try:
            await self.init_user_model()
            self.query_text_tokens, self.assist_prompt_tokens, _ = await asyncio.gather(
                self.num_tokens(self.query_text, 4),
                self.num_tokens(self.assist_prompt, 7),
                self.check_in_works(),
            )

            if self.check_long_query:
                raise LongQueryError(
                    f'{self.user.display_name if self.user.is_authenticated else "Дорогой друг"}, слишком большой текст запроса.\n'
                    'Попробуйте сформулировать его короче.'
                )

            await asyncio.gather(
                self.check_balance(self.query_text_tokens + self.assist_prompt_tokens),
                self.get_prompt()
            )

            if self.model.provider_cdk == ProviderCDK.ANTHROPIC:
                request_method = self.cdk_ap_stream_request if self.stream else self.cdk_ap_request
            else:
                request_method = self.cdk_stream_request if self.stream else self.cdk_request
            await request_method()

            asyncio.create_task(self.create_history_ai())

        except Exception as err:
            _, wrapped_exception, trace = await handle_exceptions(err, include_traceback=True)
            logger.error(trace)
            raise wrapped_exception
        finally:
            await self.del_mess_in_redis()

    async def check_balance(self, tokens_amount) -> int:
        if self.model.is_free:
            return True
        price_per_token = Decimal(self.model.incoming_price) / Decimal('100000')
        incoming_price_total = price_per_token * Decimal(tokens_amount)
        outgoing_price_total = Decimal(self.model.outgoing_price) * Decimal('0.03')
        required_amount = incoming_price_total + outgoing_price_total
        raise LowTokensBalanceError(f'Недостаточно средств. Вы исчерпали свой лимит. Текущая транзакция требует {required_amount}')

    def _get_transport_sync(self, timeout):
        """
        Синхронная функция для получения транспорта. Если proxy не загружен,
        обновляет модель из базы.
        """
        if self.model.proxy:
            proxy_transport = AsyncProxyTransport.from_url(self.model.proxy.proxy_socks)
            return httpx.AsyncClient(transport=proxy_transport, timeout=timeout)
        return httpx.AsyncClient(timeout=timeout)

    async def get_transport(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(connect=10.0, read=600.0, write=20.0, pool=10.0)
        return await sync_to_async(self._get_transport_sync)(timeout)

    async def cdk_request(self) -> None:
        """Делает запрос и выключает typing."""
        model_title = self.model.title

        # anti-creativity
        if any(sub in model_title for sub in self.EXCLUDED_CREATIVITY_MODELS):
            self.creativity_controls = {}
        else:
            self.creativity_controls = dict(getattr(self, "creativity_controls", {}) or {})

        # поддержка web-поиска только у моделей с постфиксом -search-preview
        def _supports_web_search(title: str) -> bool:
            return title.endswith("-search-preview")

        if _supports_web_search(model_title):
            self.creativity_controls = {
                "web_search_options": {
                    "user_location": {
                        "type": "approximate",
                        "approximate": {
                            "country": "RU",
                            "timezone": "Europe/Moscow",
                        },
                    },
                    "search_context_size": "medium",
                }
            }

        async_transport = await self.get_transport()

        try:
            async with async_transport as transport:
                if settings.IS_TEST_GPT:
                    client = client_mock
                    await asyncio.sleep(1)
                else:
                    client = openai.AsyncClient(
                        api_key=self.model.token,
                        http_client=transport,
                        base_url=self.model.base_url,
                    )
                completion = await client.chat.completions.create(
                    model=model_title,
                    messages=self.all_prompt,
                    **self.creativity_controls,
                )

            if hasattr(completion, "choices"):
                image_tokens = getattr(getattr(completion.usage, "prompt_tokens_details", {}), "image_tokens", 0) or 0
                self.return_text = completion.choices[0].message.content
                self.return_text_tokens = completion.usage.completion_tokens
                self.query_text_tokens = completion.usage.prompt_tokens + image_tokens
                return

            formatted_dict = pprint.pformat(completion.__dict__, indent=4)
            raise ValueChoicesError(f"`GetAnswerGPT`, ответ не содержит полей 'choices':\n{formatted_dict}")

        except openai.APIConnectionError as req_err:
            raise OpenAIConnectionError(f'`GetAnswerGPT`, проблемы соединения: {req_err}') from req_err
        except openai.APIStatusError as http_err:
            raise OpenAIResponseError(
                f'`GetAnswerGPT`, ответ сервера был получен, но код состояния указывает на ошибку: {http_err}'
            ) from http_err
        except Exception as error:
            raise UnhandledError(
                f'Необработанная ошибка в `GetAnswerGPT.cdk_request_to_openai()`: {error}'
            ) from error

    async def cdk_stream_request(self) -> None:
        """Делает запрос в OpenAI и выключает typing."""
        try:
            model_title = self.model.title
            if any(substring in model_title for substring in self.EXCLUDED_CREATIVITY_MODELS):
                self.creativity_controls = {}

            async_transport = await self.get_transport()

            async with async_transport as transport:
                client = openai.AsyncOpenAI(
                    api_key=self.model.token,
                    http_client=transport,
                    base_url=self.model.base_url,
                )
                if settings.IS_TEST_GPT:
                    stream = text_stream_generator(chunk_size=20)
                else:
                    stream = await client.chat.completions.create(
                        model=model_title,
                        messages=self.all_prompt,
                        stream=self.stream,
                        **self.creativity_controls
                    )
                first_chunk = True
                normalized_piece = ""
                async for chunk in stream:
                    piece = chunk.choices[0].delta.content or ""
                    if piece:
                        normalized_piece = normalize_text(piece)
                    self.return_text += normalized_piece
                    await self.send_chunk_to_websocket(self.return_text, is_start=first_chunk, is_end=False)
                    if first_chunk:
                        first_chunk = False
                await self.send_chunk_to_websocket("", is_end=True)
                await self.finite_tokens()

        except openai.APIStatusError as http_err:
            class_name = self.__class__.__name__
            raise OpenAIResponseError(f'`{class_name}`, ответ сервера был получен, но код состояния указывает на ошибку: {http_err}') from http_err
        except openai.APIConnectionError as req_err:
            class_name = self.__class__.__name__
            raise OpenAIConnectionError(f'`{class_name}`, проблемы соединения: {req_err}') from req_err
        except Exception as error:
            class_name = self.__class__.__name__
            raise UnhandledError(f'Необработанная ошибка в `{class_name}.cdk_stream_request_to_openai()`: {error}') from error

    async def cdk_ap_request(self) -> None:
        """Делает запрос и выключает typing."""
        try:

            async_transport = await self.get_transport()
            system_message, filtered_prompt = await self.split_prompt_by_anthropic()

            async with async_transport as transport:
                client = anthropic.AsyncAnthropic(
                    api_key=self.model.token,
                    http_client=transport,
                    base_url=self.model.base_url,
                )
                completion = await client.messages.create(
                    model=self.model.title,
                    system=system_message,
                    max_tokens=2500,
                    messages=filtered_prompt,
                    temperature=self.creativity_controls.get("temperature", 1)
                )
            if hasattr(completion, 'content'):
                self.return_text = completion.content[0].text
                self.return_text_tokens = completion.usage.output_tokens
                self.query_text_tokens = completion.usage.input_tokens
                return
            formatted_dict = pprint.pformat(completion.__dict__, indent=4)
            raise ValueChoicesError(f"`GetAnswerGPT`, ответ не содержит полей 'choices':\n{formatted_dict}")

        except anthropic.APIError as req_err:
            raise OpenAIConnectionError(f'`GetAnswerGPT`, проблемы соединения: {req_err}') from req_err
        except Exception as error:
            raise UnhandledError(f'Необработанная ошибка в `GetAnswerGPT.cdk_request_to_openai()`: {error}') from error

    async def cdk_ap_stream_request(self) -> None:
        try:

            if self._is_search_preview_model():
                self.stream = False
                return await self.cdk_request()

            async_transport = await self.get_transport()
            system_message, filtered_prompt = await self.split_prompt_by_anthropic()

            async with async_transport as transport:
                client = anthropic.AsyncAnthropic(
                    api_key=self.model.token,
                    http_client=transport,
                    base_url=self.model.base_url,
                )
                async with client.messages.stream(
                    model=self.model.title,
                    system=system_message,
                    max_tokens=2500,
                    messages=filtered_prompt,
                    temperature=self.creativity_controls.get("temperature", 1),
                ) as stream:
                    first_chunk = True
                    normalized_piece = ""
                    async for event in stream:
                        if event.type == "content_block_delta":
                            piece = event.delta.text
                            if piece:
                                normalized_piece = normalize_text(piece)
                            self.return_text += normalized_piece
                            await self.send_chunk_to_websocket(self.return_text, is_start=first_chunk, is_end=False)
                            if first_chunk:
                                first_chunk = False
                        elif event.type == "ping":
                            pass
                        elif event.type == "error":
                            raise Exception(f"Ошибка в потоке: {event.error['message']}")

                    await self.send_chunk_to_websocket("", is_end=True)
                    message = await stream.get_final_message()
                    if hasattr(message, 'usage'):
                        self.return_text_tokens = message.usage.output_tokens
                        self.query_text_tokens = message.usage.input_tokens

        except anthropic.APIError as http_err:
            class_name = self.__class__.__name__
            raise OpenAIResponseError(f'`{class_name}`, ответ сервера был получен, но код состояния указывает на ошибку: {http_err}') from http_err
        except Exception as error:
            class_name = self.__class__.__name__
            raise UnhandledError(f'Необработанная ошибка в `{class_name}.cdk_stream_request_to_openai()`: {error}') from error

    async def split_prompt_by_anthropic(self):
        filtered_prompt = []
        system_message = None
        for msg in self.all_prompt:
            if msg["role"] == "system" and system_message is None:
                system_message = msg["content"]
            else:
                filtered_prompt.append(msg)
        return system_message, filtered_prompt

    async def finite_tokens(self):
        all_prompt_text = json.dumps(self.all_prompt, ensure_ascii=False)
        self.query_text_tokens, self.return_text_tokens = await asyncio.gather(
            self.num_tokens(all_prompt_text),
            self.num_tokens(self.return_text, 4),
        )

    async def create_history_ai(self):
        """Создаём запись истории в БД для моделей поддерживающих асинхронное сохранение."""
        try:
            await self.history_model.objects.acreate(
                user=self.user if self.user.is_authenticated else None,
                room_group_name=self.room_group_name if hasattr(self, 'room_group_name') else None,
                question=self.query_text,
                question_tokens=self.query_text_tokens,
                question_token_price=self.model.outgoing_price,
                image_url=self.image_url,
                answer=self.return_text,
                answer_tokens=self.return_text_tokens,
                answer_token_price=self.model.incoming_price,
                consumer=self.consumer,
                model=self.model
            )
        except Exception as error:
            raise UnhandledError(f'Необработанная ошибка в `GetAnswerGPT.create_history_ai()`: {error}') from error

    async def num_tokens(self, text: str, corr_token: int = 0) -> int:
        """Считает количество токенов.
        ## Args:
        - text (`str`): текс для которого возвращается количество
        - corr_token (`int`): количество токенов для ролей и разделителей

        """
        try:
            encoding = await tiktoken_async.encoding_for_model(self.model.title)
        except KeyError:
            encoding = await tiktoken_async.get_encoding("cl100k_base")
        return len(encoding.encode(text)) + corr_token

    async def remove_from_prompt(self, role: str, text: str) -> None:
        """Удалить последнюю запись из списка all_prompt, если первые 15 слов совпадают без учета HTML и Markdown тегов."""
        if not self.all_prompt:
            return

        last_prompt = self.all_prompt[-1]

        if last_prompt['role'] == role:

            last_prompt_words = self.clean_and_split_text(last_prompt['content'])
            input_text_words = self.clean_and_split_text(text)

            if last_prompt_words == input_text_words:
                del self.all_prompt[-1]

    async def insert_to_prompt(self, role: str, content: str) -> None:
        """Добавляет элемент в начало списка all_prompt."""
        self.all_prompt = [{'role': role, 'content': content}] + self.all_prompt

    async def append_to_prompt(self, role: str, content: str) -> None:
        """Добавляет элемент в конец списка all_prompt."""
        self.all_prompt.append({'role': role, 'content': content})

    async def insert_to_prompt_image(self, role: str, content: str) -> None:
        """Добавляет элемент в начало списка all_prompt."""
        self.all_prompt = [{'role': role, 'content': [{"type": "image_url", "image_url": {"url": content}}]}] + self.all_prompt

    async def append_to_prompt_image(self, role: str, content: str) -> None:
        """Добавляет элемент в конец списка all_prompt."""
        self.all_prompt.append({"role": role, "content": [{"type": "image_url", "image_url": {"url": content, "detail": "high"}}]})

    def _is_search_preview_model(self) -> bool:
        title = getattr(self.model, "title", "") or ""
        return title.endswith("-search-preview")

    async def get_prompt(self) -> None:
        """Prompt для запроса в OpenAI и модель user."""
        self.all_prompt = []

        system_role, system_prompt = (
            ('user', f"# AI permanent identity, behavior, and style\n{self.assist_prompt}")
            if self.model.title.startswith(('o1', 'o3')) else ('system', self.assist_prompt)
        )

        # ВЕТКА ДЛЯ -search-preview: только мастер-промпт и последний вопрос
        if self._is_search_preview_model():
            await self.insert_to_prompt(system_role, system_prompt)
            await self.append_to_prompt('user', self.query_text)
            return

        # --- Обычная ветка для несёрчевых моделей --
        history = []
        if self.user.is_authenticated:
            history = [
                row async for row in self.history_model.objects
                .filter(
                    user=self.user,
                    created_at__range=[self.time_start, self.current_time],
                    consumer=self.consumer,
                )
                .exclude(answer__isnull=True)
                .values('question', 'question_tokens', 'image_url', 'answer', 'answer_tokens')
            ]

        if self.reply_to_message_text:
            reply_to_message_tokens = await self.num_tokens(self.reply_to_message_text, 4)
            self.query_text_tokens += reply_to_message_tokens

        token_counter = self.query_text_tokens + self.assist_prompt_tokens
        for item in reversed(history):
            question_tokens = item.get('question_tokens', 0)
            answer_tokens = item.get('answer_tokens', 0)
            token_counter += question_tokens + answer_tokens + 11

            if token_counter >= self.model.context_window:
                break

            await self.insert_to_prompt('assistant', item['answer'])
            await self.insert_to_prompt('user', item['question'])
            if item['image_url']:
                await self.insert_to_prompt_image('user', item['image_url'])

        if self.reply_to_message_text:
            await self.remove_from_prompt('assistant', self.reply_to_message_text)
            await self.append_to_prompt(
                'assistant',
                f'A message to analyze that you are asked to respond to: {self.reply_to_message_text}'
            )

        await self.insert_to_prompt(system_role, system_prompt)
        if self.image_url:
            await self.append_to_prompt_image('user', self.image_url)
        await self.append_to_prompt('user', self.query_text)

    def _is_openai(self) -> bool:
        return getattr(self.model, "provider_cdk", None) == ProviderCDK.OPENAI

    def _is_mini_or_nano(self, title: str | None = None) -> bool:
        t = (title or getattr(self.model, "title", "") or "").lower()
        return ("-mini" in t) or ("-nano" in t)

    def _looks_like_web_search(self) -> bool:
        """Грубая эвристика: запрос «пахнет» онлайн-поиском/новостями/ценами/ссылками и т.п."""
        q = (self.query_text or "").lower()
        patterns = (
            r"\bнайд[иё]\b", r"\bпоиск\b", r"\bпоищи\b", r"\bпосмотри(те)?\b",
            r"\bчто нового\b", r"\bновост", r"\bсегодня\b", r"\bвчера\b",
            r"\bцена( сейчас| сегодня)?\b", r"\bкурс\b", r"\bрасписани[ея]\b",
            r"\bкогда\b", r"http[s]?://", r"\bsite:[\w\.\-]+", r"\bрелиз\b",
            r"\bобновлени", r"\bupdate\b", r"\bкто сейчас\b",
            r"\bпрогноз\b", r"\bакци[ия]\b", r"\bбирж[аи]\b", r"\bстоимость\b",
            # на всякий случай EN-маркеры
            r"\bfind\b", r"\bsearch\b", r"\blook up\b", r"\blatest\b", r"\btoday\b", r"\bnews\b",
        )
        return any(re.search(p, q) for p in patterns)

    async def init_user_model(self):
        """Инициация активной модели юзера и начального времени истории в prompt для запроса."""
        if self.user.is_authenticated:
            queryset = UserGptModels.objects.select_related('active_model__proxy', 'active_prompt')
            self.user_models, created = await queryset.aget_or_create(
                user=self.user, defaults={'time_start': self.current_time}
            )
            if not self.user_models.active_model:
                self.model = await GptModels.objects.select_related('proxy').filter(
                    is_default=True, consumer=self.consumer
                ).afirst()
                self.user_models.active_model = self.model
                await self.user_models.asave()
            else:
                self.model = self.user_models.active_model

            if not created and self.model:
                time_window = timedelta(minutes=self.model.time_window)
                self.time_start = max(self.current_time - time_window, self.user_models.time_start)
            else:
                self.time_start = self.current_time
        else:
            self.model = await GptModels.objects.select_related('proxy').filter(
                is_default=True, consumer=self.consumer
            ).afirst()
            self.time_start = self.current_time

        # try:
        #     if self._looks_like_web_search() and self._is_openai() and not self._is_mini_or_nano():
        #         if not self._is_search_preview_model():
        #             search_model = await GptModels.objects.select_related('proxy').filter(
        #                 title="gpt-4o-search-preview", consumer=self.consumer
        #             ).afirst()
        #             if not search_model:
        #                 search_model = await GptModels.objects.select_related('proxy').filter(
        #                     title="gpt-4o-search-preview"
        #                 ).afirst()

        #             if search_model:
        #                 self.model = search_model
        # except Exception:
        #     pass

    async def check_in_works(self) -> bool:
        """Проверяет нет ли уже в работе этого запроса в Redis и добавляет в противном случае."""
        queries = await self.redis_client.lrange(f'gpt_user:{self.user.id}', 0, -1)
        if self.query_text in queries:
            raise InWorkError('Запрос уже находится в работе.')
        await self.redis_client.lpush(f'gpt_user:{self.user.id}', self.query_text)

    async def del_mess_in_redis(self) -> None:
        """Удаляет входящее сообщение из Redis."""
        await self.redis_client.lrem(f'gpt_user:{self.user.id}', 1, self.query_text.encode('utf-8'))
