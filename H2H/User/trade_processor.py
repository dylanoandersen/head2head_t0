from all_players.models import Player
from django.db import transaction
from rest_framework.response import Response

def process_trade(user_team, opponent_team, user_players, opponent_players, currency_offered, currency_requested):
    # Validate currency
    if user_team.author.profile.currency < currency_offered:
        return Response({"error": "You do not have enough currency to offer."}, status=400)
    if opponent_team.author.profile.currency < currency_requested:
        return Response({"error": "Opponent does not have enough currency to fulfill the request."}, status=400)

    # Process trade in a transaction
    with transaction.atomic():
        # Swap players
        for position, user_player_ids in user_players.items():
            opponent_player_ids = opponent_players[position]
            for user_player_id, opponent_player_id in zip(user_player_ids, opponent_player_ids):
                setattr(user_team, position, str(opponent_player_id))
                setattr(opponent_team, position, str(user_player_id))

        # Update currency
        user_team.author.profile.currency -= currency_offered
        user_team.author.profile.currency += currency_requested
        user_team.author.profile.save()

        opponent_team.author.profile.currency += currency_offered
        opponent_team.author.profile.currency -= currency_requested
        opponent_team.author.profile.save()

        # Save updated teams
        user_team.save()
        opponent_team.save()