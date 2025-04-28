import json
import random
import itertools
import math
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.db import connection
from .models import League, Matchup, Team
from all_players.models import Player
from django.contrib.auth.models import User




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
        message_type = data.get('message', {}).get('type')

        if message_type == 'make_pick':
            print("Received make_pick message:", data)
            await self.handle_pick(data['message'])

    #async def send_draft_update(self, event):
     #   # Send the draft update to the WebSocket client
      #  await self.send(text_data=json.dumps(event["message"]))

    async def handle_pick(self, message):
        from .models import Draft, Team, League
        from all_players.models import Player
        from django.contrib.auth.models import User

        user_id = message['user_id']
        player_id = message['player_id']
        position = message['position']

        try:
            draft = await sync_to_async(Draft.objects.get)(league__id=self.league_id)
            player = await sync_to_async(Player.objects.get)(id=player_id)
            user = await sync_to_async(User.objects.get)(id=user_id)
            league = await sync_to_async(League.objects.get)(id=self.league_id)
        except (Draft.DoesNotExist, Player.DoesNotExist, User.DoesNotExist, League.DoesNotExist) as e:
            print(f"Error: {e}")
            await self.check_draft_completion(league)
            return

        if draft.get_next_pick() != user_id:
            print(f"Error: It's not the user's turn. Expected user {draft.get_next_pick()}, but got {user_id}.")
            await self.check_draft_completion(league)
            return

        if any(pick['player_id'] == player_id for pick in draft.picks):
            print(f"Error: Player {player_id} has already been picked.")
            await self.check_draft_completion(league)
            return

        team, created = await sync_to_async(Team.objects.get_or_create)(author=user, league=league)
        print(f"Team before pick: QB={team.QB}, RB1={team.RB1}, RB2={team.RB2}, WR1={team.WR1}, WR2={team.WR2}, TE={team.TE}, FLX={team.FLX}, K={team.K}, Bench={team.BN1}, {team.BN2}, {team.BN3}, {team.BN4}, {team.BN5}, {team.BN6}")  # Debugging log
        print(f"Attempting to add player {player.firstName} {player.lastName} (ID: {player_id}, Position: {position}) to the team.")

        def is_position_empty(value):
            return value in [None, 'N/A', 'NULL']
        if position in ['Defense', 'DEF'] and is_position_empty(team.DEF):
            team.DEF = player.id
        elif position == 'Quarterback' and is_position_empty(team.QB):
            team.QB = player.id
        elif position == 'Running Back' and is_position_empty(team.RB1):
            team.RB1 = player.id
        elif position == 'Running Back' and is_position_empty(team.RB2):
            team.RB2 = player.id
        elif position == 'Wide Receiver' and is_position_empty(team.WR1):
            team.WR1 = player.id
        elif position == 'Wide Receiver' and is_position_empty(team.WR2):
            team.WR2 = player.id
        elif position == 'Tight End' and is_position_empty(team.TE):
            team.TE = player.id
        elif position == 'Place kicker' and is_position_empty(team.K):
            team.K = player.id
        elif position == 'Flex' and is_position_empty(team.FLX) and player.position in ['Running Back', 'Wide Receiver', 'Tight End']:
            team.FLX = player.id
        elif position == 'Bench' and any(is_position_empty(getattr(team, bench_spot)) for bench_spot in ['BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6']):
            for bench_spot in ['BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6']:
                if is_position_empty(getattr(team, bench_spot)):
                    setattr(team, bench_spot, player.id)
                    break
        else:
            print(f"Error: Invalid position or already filled for position {position}.")
            print(f"Team state: QB={team.QB}, RB1={team.RB1}, RB2={team.RB2}, WR1={team.WR1}, WR2={team.WR2}, TE={team.TE}, FLX={team.FLX}, K={team.K}, Bench={team.BN1}, {team.BN2}, {team.BN3}, {team.BN4}, {team.BN5}, {team.BN6}")  # Debugging log
            await self.check_draft_completion(league)
            return

        await sync_to_async(team.save)()
        print(f"Team after pick: QB={team.QB}, RB1={team.RB1}, RB2={team.RB2}, WR1={team.WR1}, WR2={team.WR2}, TE={team.TE}, FLX={team.FLX}, K={team.K}, DEF={team.DEF}, Bench={team.BN1}, {team.BN2}, {team.BN3}, {team.BN4}, {team.BN5}, {team.BN6}")  # Debugging log

        draft.picks.append({'user_id': user_id, 'player_id': player_id, 'position': position})
        draft.current_pick += 1
        await sync_to_async(draft.save)()

        updated_positions = {
            "QB": team.QB,
            "RB1": team.RB1,
            "RB2": team.RB2,
            "WR1": team.WR1,
            "WR2": team.WR2,
            "TE": team.TE,
            "FLX": team.FLX,
            "K": team.K,
            "DEF": team.DEF,
            "BN1": team.BN1,
            "BN2": team.BN2,
            "BN3": team.BN3,
            "BN4": team.BN4,
            "BN5": team.BN5,
            "BN6": team.BN6,
        }


        print(f"Next user ID: {draft.get_next_pick()}")

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
                    'updated_positions': updated_positions,

                }
            }
        )

        await self.check_draft_completion(league)

    async def check_draft_completion(self, league):
        """Check if the draft is complete and update the league."""
        all_teams = await sync_to_async(list)(Team.objects.filter(league=league))
        all_positions_filled = all(
            team.QB not in [None, 'N/A', 'NULL'] and
            team.RB1 not in [None, 'N/A', 'NULL'] and
            team.RB2 not in [None, 'N/A', 'NULL'] and
            team.WR1 not in [None, 'N/A', 'NULL'] and
            team.WR2 not in [None, 'N/A', 'NULL'] and
            team.TE not in [None, 'N/A', 'NULL'] and
            team.FLX not in [None, 'N/A', 'NULL'] and
            team.K not in [None, 'N/A', 'NULL'] and
            team.DEF not in [None, 'N/A', 'NULL'] and
            all(getattr(team, f'BN{i}') not in [None, 'N/A', 'NULL'] for i in range(1, 7))
            for team in all_teams
        )

        if all_positions_filled:
            league.draftComplete = True
            await sync_to_async(league.save)()

            await sync_to_async(matchUp_creation)(league.id)

            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'draft_complete',
                    'message': 'Draft complete!',
                }
            )


    async def draft_message(self, event):
        print("Broadcasting draft message:", event['message'])
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))
    
    async def draft_complete(self, event):
        await self.send(text_data=json.dumps({
            'message': {
                'type': 'draft_complete',
                'content': event['message']
            }
        }))

def matchUp_creation(lid):
    print('Creating matchups...')
    league = League.objects.get(id = lid)
    users = list(league.users.all())
    username = [user.username for user in users]
    print(username)
    if len(username) % 2 != 0:
        username.append(None)

    all_matchups = list(itertools.combinations(username, 2))
    random.shuffle(all_matchups)

    used_matchups = set()
    rounds = []
    positions = ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLX", "K", "DEF"]


    while len(rounds) < 15:
        current_round = []
        players_used = set()

        for p1, p2 in all_matchups:
            match = tuple(sorted((p1, p2)))

            if match in used_matchups:
                continue
            if p1 in players_used or p2 in players_used:
                continue

            used_matchups.add(match)
            current_round.append(match)
            players_used.update([p for p in (p1,p2) if p is not None])

            if len(current_round) == len(username) // 2:
                break 

        if current_round:
            rounds.append(current_round)

        if len(used_matchups) == len(all_matchups):
            used_matchups = set()
            random.shuffle(all_matchups)

    print(rounds)
    for week_num, week in enumerate(rounds, 1):
        for team1_id, team2_id in week:
            print('team1: ',team1_id,'team2: ', team2_id)
            if team1_id is None or team2_id is None:
                real_team_id = team1_id or team2_id
                real_team = (User.objects.get(id=real_team_id))
                random_position = random.choice(positions)


                Matchup.objects.update_or_create(
                    league=league,
                    week=week_num,
                    team1=real_team,
                    team2=None,
                    defaults={
                        'team1score': 0,
                        'team2score': 0,
                        'position': random.choice(["QB", "RB", "WR", "TE", "K"])

                    }
                )
            else:
                team1 = User.objects.get(username=team1_id)
                team2 = User.objects.get(username=team2_id)

                Matchup.objects.update_or_create(
                    league=league,
                    week=week_num,
                    team1=team1,
                    team2=team2,
                    defaults={
                        'team1score': 0,
                        'team2score': 0,
                        'position': random.choice(["QB", "RB", "WR", "TE", "K"])

                    }
                )
