import os
import django

# Ensure Django settings are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")
django.setup()  # Initializes Django

from .espn_api import fetch_espn_data
from .models import Player


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

datas = update_espn_data()
# if datas:
#      with open("api.txt", "w") as file:
#         json.dump(datas, file)  # Saves JSON data to file with indentation

