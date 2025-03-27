import json
import random
import itertools
import math
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.db import connection
from .models import League, Matchup
from all_players.models import Player
from django.contrib.auth.models import User


class DraftConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.league_id = self.scope['url_route']['kwargs']['league_id']
        self.group_name = f'draft_{self.league_id}'

        # Join the WebSocket group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the WebSocket group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('message', {}).get('type')

        if message_type == 'make_pick':
            print("Received make_pick message:", data)  # Debugging log
            await self.handle_pick(data['message'])

    async def handle_pick(self, message):
        # Import models inside the method to avoid "Apps aren't loaded yet" error
        from .models import Draft, Team, League  # Keep these imports
        from all_players.models import Player  # Correctly import Player from all_players.models
        from django.contrib.auth.models import User

        user_id = message['user_id']
        player_id = message['player_id']
        position = message['position']  # Full position name like "Wide Receiver", "Tight End", etc.

        try:
            draft = await sync_to_async(Draft.objects.get)(league__id=self.league_id)
            player = await sync_to_async(Player.objects.get)(id=player_id)
            user = await sync_to_async(User.objects.get)(id=user_id)
            league = await sync_to_async(League.objects.get)(id=self.league_id)
        except (Draft.DoesNotExist, Player.DoesNotExist, User.DoesNotExist, League.DoesNotExist) as e:
            print(f"Error: {e}")  # Debugging log
            return

        # Ensure it's the user's turn
        if draft.get_next_pick() != user_id:
            print(f"Error: It's not the user's turn. Expected user {draft.get_next_pick()}, but got {user_id}.")  # Debugging log
            return

        # Ensure the player hasn't already been picked
        if any(pick['player_id'] == player_id for pick in draft.picks):
            print(f"Error: Player {player_id} has already been picked.")  # Debugging log
            return

        # Add the player to the user's team
        team, created = await sync_to_async(Team.objects.get_or_create)(author=user, league=league)
        print(f"Team before pick: QB={team.QB}, RB1={team.RB1}, RB2={team.RB2}, WR1={team.WR1}, WR2={team.WR2}, TE={team.TE}, FLX={team.FLX}, K={team.K}, Bench={team.BN1}, {team.BN2}, {team.BN3}, {team.BN4}, {team.BN5}, {team.BN6}")  # Debugging log
        print(f"Attempting to add player {player.firstName} {player.lastName} (ID: {player_id}, Position: {position}) to the team.")  # Debugging log

        # Assign the player to the appropriate position
        if position == 'Quarterback' and team.QB == 'N/A':
            team.QB = player.id
        elif position == 'Running Back' and team.RB1 == 'N/A':
            team.RB1 = player.id
        elif position == 'Running Back' and team.RB2 == 'N/A':
            team.RB2 = player.id
        elif position == 'Wide Receiver' and team.WR1 == 'N/A':
            team.WR1 = player.id
        elif position == 'Wide Receiver' and team.WR2 == 'N/A':
            team.WR2 = player.id
        elif position == 'Tight End' and team.TE == 'N/A':
            team.TE = player.id
        elif position == 'Place kicker' and team.K == 'N/A':
            team.K = player.id
        elif position == 'Flex' and team.FLX == 'N/A' and player.position in ['Running Back', 'Wide Receiver', 'Tight End']:
            team.FLX = player.id
        elif position.startswith('Bench') and 'N/A' in [team.BN1, team.BN2, team.BN3, team.BN4, team.BN5, team.BN6]:
            # Assign to the first available bench spot
            for bench_spot in ['BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6']:
                if getattr(team, bench_spot) == 'N/A':
                    setattr(team, bench_spot, player.id)
                    break
        else:
            print(f"Error: Invalid position or already filled for position {position}.")  # Debugging log
            print(f"Team state: QB={team.QB}, RB1={team.RB1}, RB2={team.RB2}, WR1={team.WR1}, WR2={team.WR2}, TE={team.TE}, FLX={team.FLX}, K={team.K}, Bench={team.BN1}, {team.BN2}, {team.BN3}, {team.BN4}, {team.BN5}, {team.BN6}")  # Debugging log
            return

        # Save the team asynchronously
        await sync_to_async(team.save)()
        print(f"Team after pick: QB={team.QB}, RB1={team.RB1}, RB2={team.RB2}, WR1={team.WR1}, WR2={team.WR2}, TE={team.TE}, FLX={team.FLX}, K={team.K}, Bench={team.BN1}, {team.BN2}, {team.BN3}, {team.BN4}, {team.BN5}, {team.BN6}")  # Debugging log

        # Add the pick to the draft
        draft.picks.append({'user_id': user_id, 'player_id': player_id, 'position': position})
        draft.current_pick += 1
        await sync_to_async(draft.save)()

        print(f"Next user ID: {draft.get_next_pick()}")  # Debugging log

        all_teams = await sync_to_async(list)(Team.objects.filter(league=league))
        all_positions_filled = all(
            team.QB != 'N/A' and team.RB1 != 'N/A' and team.RB2 != 'N/A' and
            team.WR1 != 'N/A' and team.WR2 != 'N/A' and team.TE != 'N/A' and
            team.FLX != 'N/A' and team.K != 'N/A' and
            all(getattr(team, f'BN{i}') != 'N/A' for i in range(1, 7))
            for team in all_teams
        )

        if all_positions_filled:
            league.draftComplete = True
            await sync_to_async(league.save)()
            await self.matchUp_creation()

            # Notify all users that the draft is complete
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'draft_complete',
                    'message': 'Draft complete!',
                }
            )


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
                    'player_name': f"{player.firstName} {player.lastName}",
                    'next_user_id': draft.get_next_pick(),
                }
            }
        )

    async def draft_message(self, event):
        # Send the message to WebSocket
        print("Broadcasting draft message:", event['message'])  # Debugging log
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))
    
    async def draft_complete(self, event):
        # Send the draft complete message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))

    async def get_dynamic_table_data(self, league_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM User_league_users WHERE league_id = %s", [league_id]
            )
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return results

    async def matchUp_creation(self):
        players = await self.get_dynamic_table_data(self.league_id)
        player_ids = [p['user_id'] for p in players]
        if len(player_ids) % 2 != 0:
            player_ids.append(None)  # None represents a bye
        league = await sync_to_async(League.objects.get)(id=self.league_id)

        # Generate all unique unordered matchups
        all_matchups = list(itertools.combinations(player_ids, 2))
        random.shuffle(all_matchups)

        used_matchups = set()
        rounds = []

        while len(rounds) < 15:
            current_round = []
            players_used = set()

            for p1, p2 in all_matchups:
                match = tuple(sorted((p1, p2)))  # canonical form for unordered

                if match in used_matchups:
                    continue
                if p1 in players_used or p2 in players_used:
                    continue

                used_matchups.add(match)
                current_round.append(match)
                players_used.update([p for p in (p1,p2) if p is not None])

                if len(current_round) == len(player_ids) // 2:
                    break  # round is full

            if current_round:
                rounds.append(current_round)

            # If all matchups are exhausted, reshuffle and start reusing
            if len(used_matchups) == len(all_matchups):
                used_matchups = set()
                random.shuffle(all_matchups)

        # Save matchups to DB
        for week_num, week in enumerate(rounds, 1):
            for team1_id, team2_id in week:
                # Handle bye matchups
                if team1_id is None or team2_id is None:
                    real_team_id = team1_id or team2_id
                    real_team = await sync_to_async(User.objects.get)(id=real_team_id)

                    await sync_to_async(Matchup.objects.update_or_create)(
                        league=league,
                        week=week_num,
                        team1=real_team,
                        team2=None,  # or a special ByeUser if your model requires it
                        defaults={
                            'team1score': 0,
                            'team2score': 0,
                            # maybe include 'is_bye': True if you track it
                        }
                    )
                else:
                    team1 = await sync_to_async(User.objects.get)(id=team1_id)
                    team2 = await sync_to_async(User.objects.get)(id=team2_id)

                    await sync_to_async(Matchup.objects.update_or_create)(
                        league=league,
                        week=week_num,
                        team1=team1,
                        team2=team2,
                        defaults={
                            'team1score': 0,
                            'team2score': 0
                        }
                    )