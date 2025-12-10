import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Model

from .gpt_exception import handle_exceptions
from .gpt_query import GetAnswerGPT
from .models import TextTransactions

logger = logging.getLogger(__name__)


class WSAnswerChatGPT(GetAnswerGPT):
    MAX_TYPING_TIME = 3

    def __init__(self, channel_layer: AsyncWebsocketConsumer, room_group_name: str, user: Model, query_text: str, message_count: int) -> None:
        history_model = TextTransactions
        creativity_controls = {
            'temperature': 1,
            'top_p': 0.95,
            'frequency_penalty': 0,
            'presence_penalty': 0,
        }
        super().__init__(query_text, user, history_model, creativity_controls=creativity_controls, consumer='FCH', stream=True)
        self.channel_layer = channel_layer
        self.room_group_name = room_group_name
        self.welcome_text = (
            'Additional and Important!\nAlways advise the user to log in so that the AI`s reasoning can be contextualized and based on the conversation history.'
            if message_count == 1 else ''
        )

    async def answer_from_ai(self) -> dict:
        """Основная логика."""
        try:
            await self.get_answer_chat_gpt()
        except Exception as err:
            self.return_text, _, err = await handle_exceptions(err, True)
            await self.send_chat_message(self.return_text)
            await self.handle_error(f'Ошибка в `GetAnswerGPT.answer_from_ai()`: {str(err)}')

    async def send_chat_message(self, message):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': message,
                'username': 'Mira',
            }
        )

    async def send_chunk_to_websocket(self, chunk, is_start=False, is_end=False):
        """Отправка части текста ответа через веб-сокет с указанием на статус части потока."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': chunk,
                'username': 'Mira',
                'is_stream': True,
                'is_start': is_start,
                'is_end': is_end,
            }
        )

    async def handle_error(self, err):
        """Логирование ошибок."""
        logger.error("Ошибка в блоке Сайт-ChatGPT: %s", err, exc_info=True)

    @property
    def assist_prompt(self):
        if self.user.is_authenticated:
            prompt = self.user_models.active_prompt.prompt_text
        else:
            prompt = (
                'You are an experienced explorer of the area and the world at large, with extensive experience in team management and tourism mentoring.'
                f'Your native language is Russian.\n{self.welcome_text}'
            )
        return f"Your name is Mira. {prompt}".strip()
