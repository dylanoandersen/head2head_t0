import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Draft, Player

class DraftConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.league_id = self.scope['url_route']['kwargs']['league_id']
        self.group_name = f'draft_{self.league_id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']

        if message['type'] == 'make_pick':
            await self.handle_pick(message)

    async def handle_pick(self, message):
        user_id = message['user_id']
        player_id = message['player_id']

        try:
            draft = await Draft.objects.get(league_id=self.league_id)
            player = await Player.objects.get(id=player_id)
        except (Draft.DoesNotExist, Player.DoesNotExist):
            return

        if draft.get_next_pick() == user_id:
            draft.picks.append({'user_id': user_id, 'player_id': player_id})
            draft.current_pick += 1
            await draft.save()

            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'draft_message',
                    'message': {'type': 'pick_made', 'user_id': user_id, 'player_id': player_id}
                }
            )

    async def draft_message(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))