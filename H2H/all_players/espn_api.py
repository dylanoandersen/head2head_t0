import sys
import os
import requests

# Add the project root directory to the PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")

# Initialize Django
import django
django.setup()

from .models import Player, Game, Player_Stats

url = "https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=20000&active=true"

#_____________________________________________________________________________________________________
# update once a year


def fetch_espn_data():

    print("🔍 Sending request to ESPN API...")
    response = requests.get(url)
    
    print(f"🔄 Received response with status code: {response.status_code}")

    if response.status_code == 200:
        print("✅ Successfully fetched data! Parsing response...")
        return response.json()  # Return JSON data
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return None


# Add status to this function as well as the model of player - makemigration migrate 
# if active status = active elif data.get('injuries', {}) or idk

def fetch_player_positions():

    for players in Player.objects.all():
        player_id = players.id

        url1 = f"https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{player_id}"

        response = requests.get(url1)

        if response.status_code == 200:
            print("✅ Successfully fetched data! Parsing response...")
            result = response.json()
            athlete = result.get('athlete', {})
            position = athlete.get('team', {})
            team_name = position.get('name', {})
            location = position.get('location', {})

            Player.objects.update_or_create(
                id=player_id,
                defaults={
                    'team': team_name,
                    'location': location
                }
            )
            print("player position added")

        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None



# _____________________________________________________________________________________________________
#update consistently
def get_game_stats():

    years = [2024, 2025]
    for year in years:
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

def get_stats():
    for games in Game.objects.all():
        EVENT_ID = games.id



        response = requests.get(url1)
        for Player in Player.objects.all():
            ATHLETE_ID = Player.id
            TEAM_ID = Player.team

            url1 = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{EVENT_ID}/competitions/{EVENT_ID}/competitors/{TEAM_ID}/roster/{ATHLETE_ID}/statistics/0"

            response = requests.get(url1)

            if response.status_code == 200:
                print("✅ Successfully fetched data! Parsing response... of STATZZZZZZZ")
                stats = response.json()
                return stats
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                return None
# data = get_stats()
# if data:
#      with open("api.txt", "w") as file:
#         json.dump(data, file)  # Saves JSON data to file with indentation




