def validate_trade(user_team, opponent_team, user_players, opponent_players, currency_offered, currency_requested):
    for position, player_ids in user_players.items():
        for player_id in player_ids:
            if getattr(user_team, position) != str(player_id):
                return False

    for position, player_ids in opponent_players.items():
        for player_id in player_ids:
            if getattr(opponent_team, position) != str(player_id):
                return False

    if set(user_players.keys()) != set(opponent_players.keys()):
        return False

    if user_team.author.profile.currency < currency_offered:
        return False
    if opponent_team.author.profile.currency < currency_requested:
        return False

    return True