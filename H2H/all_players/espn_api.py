import requests
import os
import django

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")  # Change 'head2head' to your project name

# Initialize Django
django.setup() 

from .models import Player


url = "https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=20000&active=true"

#_____________________________________________________________________________________________________


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

def fetch_player_positions():

    for players in Player.objects.all():
        player_id = players.id

        url1 = f"https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{player_id}"

        response = requests.get(url1)

        if response.status_code == 200:
            print("✅ Successfully fetched data! Parsing response...")
            result = response.json()
            athlete = result.get('athlete', {})
            position = athlete.get('position', {})
            position_abbreviation = position.get('abbreviation', {})
            if position_abbreviation == 'QB'or 'RB'or 'WR'or 'TE'or 'K':
                Player.objects.update_or_create(
                    id=player_id,
                    defaults={
                        'position': position_abbreviation
                    }
                )
                print("player position added")
            else:
                Player.objects.delete(id=player_id)
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

#x = fetch_player_positions()


# def get_stats():

#     for players in Player.objects.all():
#         player_id = players.id

#         querystring = {"id":player_id}

#         print("🔍 Sending request to ESPN API...")
#         response = requests.get(url1, headers=headers, params=querystring)
        
#         print(f"🔄 Received response with status code: {response.status_code}")

#         if response.status_code == 200:
#             print("✅ Successfully fetched data! Parsing response...")
#             stats = response.json()


#         else:
#             print(f"❌ Error {response.status_code}: {response.text}")
#             return None

# data = get_stats()
# if data:
#      with open("api.txt", "w") as file:
#         json.dump(data, file)  # Saves JSON data to file with indentation




