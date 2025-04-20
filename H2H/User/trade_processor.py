from all_players.models import Player


def process_trade(user_team, opponent_team, user_players, opponent_players):
    for position, user_player_ids in user_players.items():
        opponent_player_ids = opponent_players[position]

        for user_player_id, opponent_player_id in zip(user_player_ids, opponent_player_ids):
            # Swap players between teams
            setattr(user_team, position, str(opponent_player_id))  # Ensure IDs are strings
            setattr(opponent_team, position, str(user_player_id))  # Ensure IDs are strings

    # Save both teams
    user_team.save()
    opponent_team.save()