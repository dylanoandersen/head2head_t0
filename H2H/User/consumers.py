import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DraftConsumer(AsyncWebsocketConsumer):
    async def handle_pick(self, message):
        # Import models inside the method to avoid "Apps aren't loaded yet" error
        from .models import Draft, Player, Team, League
        from django.contrib.auth.models import User

        user_id = message['user_id']
        player_id = message['player_id']
        position = message['position']  # QB, RB, WR

        try:
            draft = await Draft.objects.aget(league__id=self.league_id)
            player = await Player.objects.aget(id=player_id)
            user = await User.objects.aget(id=user_id)
            league = await League.objects.aget(id=self.league_id)
        except (Draft.DoesNotExist, Player.DoesNotExist, User.DoesNotExist, League.DoesNotExist):
            return

        # Ensure it's the user's turn
        if draft.get_next_pick() != user_id:
            return

        # Ensure the player hasn't already been picked
        if any(pick['player_id'] == player_id for pick in draft.picks):
            return

        # Add the player to the user's team
        team, created = await Team.objects.aget_or_create(author=user, league=league)
        if position == 'QB' and team.QB == 'N/A':
            team.QB = player.name
        elif position == 'RB' and team.RB1 == 'N/A':
            team.RB1 = player.name
        elif position == 'RB' and team.RB2 == 'N/A':
            team.RB2 = player.name
        elif position == 'WR' and team.WR1 == 'N/A':
            team.WR1 = player.name
        elif position == 'WR' and team.WR2 == 'N/A':
            team.WR2 = player.name
        else:
            return  # Invalid position or already filled

        await team.save()

        # Add the pick to the draft
        draft.picks.append({'user_id': user_id, 'player_id': player_id, 'position': position})
        draft.current_pick += 1
        await draft.save()

        # Broadcast the pick to all users
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'draft_message',
                'message': {
                    'type': 'pick_made',
                    'user_id': user_id,
                    'player_id': player_id,
                    'position': position,
                    'player_name': player.name,
                }
            }
        )