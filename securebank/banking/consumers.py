import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage, ChatRoom, ChatQueue
from .chatbot import get_bot_response
from django.contrib.auth.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Add user to queue if not staff
        if not self.user.is_staff:
            await self.add_to_queue()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Remove user from queue if not staff
        if not self.user.is_staff:
            await self.remove_from_queue()

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        
        room = await self.get_room()
        
        if self.user.is_staff:
            # Staff message
            await self.save_message(room, self.user, message, is_staff=True)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': self.user.username,
                    'is_staff': True
                }
            )
        else:
            # User message
            await self.save_message(room, self.user, message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': self.user.username,
                    'is_staff': False
                }
            )

            # Check if any staff member is in the room
            if not await self.staff_in_room():
                # If no staff, send bot response
                bot_response = get_bot_response(message)
                await self.save_message(room, None, bot_response, is_bot=True)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': bot_response,
                        'username': 'Bot',
                        'is_staff': False
                    }
                )

    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        is_staff = event['is_staff']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'is_staff': is_staff
        }))

    @database_sync_to_async
    def save_message(self, room, user, message, is_bot=False, is_staff=False):
        ChatMessage.objects.create(room=room, user=user, message=message, is_bot=is_bot, is_staff=is_staff)

    @database_sync_to_async
    def get_room(self):
        return ChatRoom.objects.get_or_create(name=self.room_name)[0]

    @database_sync_to_async
    def add_to_queue(self):
        room = ChatRoom.objects.get_or_create(name=self.room_name)[0]
        queue, _ = ChatQueue.objects.get_or_create(room=room)
        queue.users.add(self.user)

    @database_sync_to_async
    def remove_from_queue(self):
        room = ChatRoom.objects.get(name=self.room_name)
        queue = ChatQueue.objects.get(room=room)
        queue.users.remove(self.user)

    @database_sync_to_async
    def staff_in_room(self):
        room = ChatRoom.objects.get(name=self.room_name)
        return ChatMessage.objects.filter(room=room, is_staff=True).exists()

class AgentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = 'agent_room'
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial queue status
        await self.send_queue_status()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json['action']
        
        if action == 'take_next':
            next_user = await self.get_next_user_in_queue()
            if next_user:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'agent_assigned',
                        'user_id': next_user.id,
                        'agent_id': self.scope['user'].id
                    }
                )

    async def queue_status(self, event):
        await self.send(text_data=json.dumps(event))

    async def agent_assigned(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_next_user_in_queue(self):
        queue = ChatQueue.objects.first()
        if queue and queue.users.exists():
            return queue.users.first()
        return None

    @database_sync_to_async
    def send_queue_status(self):
        queues = ChatQueue.objects.all()
        queue_status = {str(queue.room.name): queue.users.count() for queue in queues}
        return self.send(text_data=json.dumps({
            'type': 'queue_status',
            'queues': queue_status
        }))