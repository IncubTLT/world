import asyncio
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from config.async_redis import AsyncRedisClient


class ChatConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_client = AsyncRedisClient.get_client()

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"chat_{self.room_id}"
        self.message_count = 0

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        from apps.ai.utilities import WSAnswerChatGPT
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        user = self.scope['user']
        room_group_name = self.room_group_name
        redis_key = f'chat:{room_group_name}:user:{user.id}:lock'

        time_limit = (2, 'ы') if user.is_authenticated else (5, ', для незарегистрированных пользователей')
        if await self.redis_client.get(redis_key):
            await self.send_error(f'Запросы можно отправлять не чаще, чем раз в {time_limit[0]} секунд{time_limit[1]}.')
            return None

        await self.redis_client.set(redis_key, "locked", ex=time_limit[0])

        self.message_count += 1
        send_mira = {
            'channel_layer': self.channel_layer,
            'room_group_name': room_group_name,
            'user': user,
            'query_text': message,
            'message_count': self.message_count,
        }

        answer_gpt_instance = WSAnswerChatGPT(**send_mira)
        asyncio.create_task(answer_gpt_instance.answer_from_ai())

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': message,
                'username': user.username,
            }
        )

    async def chat_message(self, event):
        """Отправка сообщения на клиент"""
        message = event['message']
        username = event['username']
        is_stream = event.get('is_stream', False)
        is_start = event.get('is_start', False)
        is_end = event.get('is_end', False)

        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'is_stream': is_stream,
            'is_start': is_start,
            'is_end': is_end,
        }))

    async def send_error(self, error_message):
        await self.send(text_data=json.dumps({
            'message': error_message,
        }))
