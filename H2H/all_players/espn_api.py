import sys
import os
import requests
import json
from .models import Player

#team_id = [(1, 'Falcons'), (2, 'Bills'), (3, 'Bears'), (4, 'Bengals'), (5, 'Browns'), (6, 'Cowboys'), (7, 'Broncos'), (8, 'Lions'), (9, 'Packers'), (34, 'Texans'), (11, 'Colts'), (30, 'Jaguars'), (12, 'Chiefs'), (14, 'Rams'), (24, 'Chargers'), (15, 'Dolphins'), (16, 'Vikings'), (17, 'Patriots'), (18, 'Saints'), (19, 'Giants'), (20, 'Jets'), (13, 'Raiders'), (21, 'Eagles'), (23, 'Steelers'), (25, '49ers'), (26, 'Seahawks'), (27, 'Buccaneers'), (10, 'Titans'), (22, 'Cardinals'), (28, 'Commanders'), (33, 'Ravens'), (29, 'Panthers')]

# Add the project root directory to the PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")

# Initialize Django
import django
#django.setup()

from .models import Player, Game, Player_Stats

#_____________________________________________________________________________________________________
# update once a year


def fetch_espn_data():
    url = "https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=20000&active=true"

    print("🔍 Sending request to ESPN API...")
    response = requests.get(url)
    
    print(f"🔄 Received response with status code: {response.status_code}")

    if response.status_code == 200:
        print("✅ Successfully fetched data! Parsing response...")
        return response.json()  # Return JSON data
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return None

def fetch_def_info():
    url1 = f"https://api.sleeper.app/v1/players/nfl"

    response = requests.get(url1)

    if response.status_code == 200:
        print("✅ Successfully fetched data! Parsing response...")
        return response.json()
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        pp=1
        return pp

# Get all teams DEF
# x = fetch_def_info()
# for z,y in x.items():
#     if y.get('position') == 'DEF':
#         print('found DEF')
#         Player.objects.update_or_create(
#             id = y.get('player_id'),
#             defaults={
#                 'lastName': y.get('last_name'),
#                 'firstName': y.get('first_name'),
#                 'position': y.get('position'),
#                 'team': y.get('last_name')
#             }
#         )


# Add status to this function as well as the model of player - makemigration migrate 
# if active status = active elif data.get('injuries', {}) or idk

def fetch_player_positions(player_id):

    url1 = f"https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{player_id}"

    response = requests.get(url1)

    if response.status_code == 200:
        print("✅ Successfully fetched data! Parsing response...")
        return response.json()
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        pp=1
        return pp



# _____________________________________________________________________________________________________
# all games
def get_game_stats(year):

    url1 = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?limit=1000&dates={year}"

    response = requests.get(url1)
    
    print(f"🔄 Received response with status code: {response.status_code}")

    if response.status_code == 200:
        print("✅ Successfully fetched data! Parsing response... of GAME")
        stats = response.json()
        return stats

    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return None

def game_details(game_id):
        url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={game_id}'
        response = requests.get(url)

        # Handle API response and log results
        if response.status_code == 200:
            print("✅ Successfully fetched data! Parsing response...")
            stats = response.json()
            return stats
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return

def get_stats(game_id, team_id, player_id):

    url1 = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{game_id}/competitions/{game_id}/competitors/{team_id}/roster/{player_id}/statistics/0"

    response = requests.get(url1)

    if response.status_code == 200:
        print("✅ Successfully fetched data! Parsing response... of STATZZZZZZZ")
        stats = response.json()
        return stats
    else:
        pp = 1
        print(f"❌ Error {response.status_code}: {response.text}")
        return pp

def get_def_stats(game_id, team_id):
    url = f'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{game_id}/competitions/{game_id}/competitors/{team_id}/statistics'
    response = requests.get(url)

    if response.status_code == 200:
        print("✅ Successfully fetched data! Parsing response... of STATZZZZZZZ of DEF")
        stats = response.json()
        return stats
    else:
        pp = 1
        print(f"❌ Error {response.status_code}: {response.text}")
        return pp



# data = get_game_stats(2025)
# if data:
#      with open("api.txt", "w") as file:
#         json.dump(data, file, indent=4)  # Saves JSON data to file with indentation