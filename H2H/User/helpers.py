from all_players.models import Player


def validate_trade(user_team, opponent_team, user_players, opponent_players):
    # Ensure all players belong to their respective teams
    for position, player_ids in user_players.items():
        for player_id in player_ids:  # Iterate through the array of player IDs
            if getattr(user_team, position) != str(player_id):  # Compare as strings
                return False  # Player does not belong to the user's team

    for position, player_ids in opponent_players.items():
        for player_id in player_ids:  # Iterate through the array of player IDs
            if getattr(opponent_team, position) != str(player_id):  # Compare as strings
                return False  # Player does not belong to the opponent's team

    # Ensure the positions being traded match
    if set(user_players.keys()) != set(opponent_players.keys()):
        return False

    return True