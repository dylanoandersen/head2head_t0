import os
import django

# Ensure Django settings are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")
django.setup()  # Initializes Django

from .espn_api import fetch_espn_data, get_game_stats
from .models import Player, Game

# update once a year
def update_espn_data():
    data = fetch_espn_data()

    players = data["items"]  # Extract the list of players

    # Loop through the list and insert only active players
    for player in players:
        if player.get('active', True):
            Player.objects.update_or_create(
                id=player['id'],  # Ensure ID is the primary key
                defaults={
                    'firstName': player.get('firstName', ''),
                    'lastName': player.get('lastName', ''),
                    'weight': player.get('weight', 0),
                    'displayHeight': player.get('displayHeight', ''),
                    'age': player.get('age', 0),
                    'experience': player.get('experience', ''),
                    'jersey': player.get('jersey', 0)
                }
            )
#______________________________________________________________________
# update consistently 

def update_game_data():
    data = get_game_stats()
    events = data.get("events", [])

    for event in events:
        id = event.get("id","")
        date = event.get("date", "")

        season_type = event.get("season", {}).get("slug", "")

        if event.get("season", {}).get("year", 0) != 2024:
            continue

        game = event.get("competitions", [])

        for competition in game:
            competitors = competition.get("competitors", [])
            for competitor in competitors:
                if competitor.get("homeAway") == "home":
                    home_team = competitor.get("team", {}).get("displayName", "")
                    home_score = competitor.get("score", "")
                else:
                    away_team = competitor.get("team", {}).get("displayName", "")
                    away_score = competitor.get("score", "")

            Game.objects.update_or_create(
                id=id,
                defaults={
                    'season_type': season_type,
                    'date': date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score
                }
            )
            print("game data added")
x = update_game_data()


# def update_stats():

#     data = get_stats()

#     # navigating to correct part of dictionary
#     categories = data.get("splits", {}).get("categories", [])
#     passing_category = next((cat for cat in categories if cat.get("name") == "passing"), None)

#     # check if info is in stats
#     if passing_category:
#         stats = passing_category.get("stats", [])
#         target_names = ["passingAttempts", "completions", "completionPct", "passingYards", "passingTouchdowns"]

#         extracted_values = {}
#         for stat in stats:
#             if stat.get("name") in target_names:
#                 if stat.get("name") == "passingYards" or "passingTouchdowns":
#                     extracted_values[stat["name"]] = {stat.get("displayValue", "N/A"),
#                                                       stat.get("perGameValue", "N/A")}
#                     continue
#                 extracted_values[stat["name"]] = stat.get("displayValue", "N/A")

#     else:
#         print('nothing retrieved')