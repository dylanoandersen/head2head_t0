from all_players.models import Player
from django.db import transaction
from rest_framework.response import Response

from django.db import transaction

def process_trade(user_team, opponent_team, user_players, opponent_players, currency_offered, currency_requested):
    # Validate currency
    if user_team.author.profile.currency < currency_offered:
        raise ValueError("You do not have enough currency to offer.")
    if opponent_team.author.profile.currency < currency_requested:
        raise ValueError("Opponent does not have enough currency to fulfill the request.")

    # Define valid interchangeable positions
    valid_trades = {
        "WR1": ["WR2"],
        "WR2": ["WR1"],
        "RB1": ["RB2"],
        "RB2": ["RB1"],
        "BN1": ["BN2", "BN3", "BN4", "BN5", "BN6"],
        "BN2": ["BN1", "BN3", "BN4", "BN5", "BN6"],
        "BN3": ["BN1", "BN2", "BN4", "BN5", "BN6"],
        "BN4": ["BN1", "BN2", "BN3", "BN5", "BN6"],
        "BN5": ["BN1", "BN2", "BN3", "BN4", "BN6"],
        "BN6": ["BN1", "BN2", "BN3", "BN4", "BN5"],
    }

    # Process trade in a transaction
    with transaction.atomic():
        # Swap players
        for position, user_player_id in user_players.items():
            opponent_player_id = opponent_players.get(position)

            # Handle interchangeable positions
            if not opponent_player_id:
                for interchangeable_position in valid_trades.get(position, []):
                    if interchangeable_position in opponent_players:
                        opponent_player_id = opponent_players[interchangeable_position]
                        break

            if not opponent_player_id:
                raise ValueError(f"Invalid trade. No matching player for position {position}.")

            # Ensure valid player IDs are swapped
            setattr(user_team, position, opponent_player_id)
            setattr(opponent_team, position, user_player_id)

        # Update currency
        user_team.author.profile.currency -= currency_offered
        user_team.author.profile.currency += currency_requested
        user_team.author.profile.save()

        opponent_team.author.profile.currency += currency_offered
        opponent_team.author.profile.currency -= currency_requested
        opponent_team.author.profile.save()

        user_team.save()
        opponent_team.save()