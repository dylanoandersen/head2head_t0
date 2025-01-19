import os
import django
from datetime import datetime

# Ensure Django settings are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")
django.setup()  # Initializes Django

from .espn_api import fetch_espn_data, get_game_stats, get_stats, fetch_player_positions
from .models import Player, Game

# update once a year
def update_espn_data():
    data = fetch_espn_data()

    players = data["items"]  # Extract the list of players

    # Loop through the list and insert only active players
    for player in players:
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
def update_player_positions():
    for player in Player.objects.all():
        result = fetch_player_positions(player.id)
        
        athlete = result.get('athlete', {})

        position = athlete.get('position', {})
        player_pos = position.get('name', '')

        team = athlete.get('team', {})
        team_name = team.get('name', '')
        location = team.get('location', '')

        if athlete.get('active', '') == True:
            if 'injuries' in athlete:
                status = athlete.get('injuries', [])
                for s in status:
                    status = s.get('type', {}).get('name', '')
            else:
                status = 'Active'
        if athlete.get('active', '') == False:
            Player.objects.filter(id=player.id).delete()
            print("player deleted !!!!!!!!!!!!!!!")
        Player.objects.update_or_create(
            id=player.id,
            defaults={
                'status': status,
                'team': team_name,
                'location': location,
                'position': player_pos
            }
        )
        print("player position added")
#______________________________________________________________________

# update consistently 

def today_games():
    teams_playing_today = []

    for games in Game:
        date_string = games.date

        date_from_string = datetime.strptime(date_string, "%Y-%m-%dT%H:%MZ").date()

        today = datetime.today().date()

        # Compare dates
        if date_from_string == today:
            print("The dates match!")

        game = games.get("competitions", [])
        for competition in game:
            competitors = competition.get("competitors", [])
            for competitor in competitors:
                team = competitor.get("team", {}).get("displayName", "")
                teams_playing_today.append(team)

    return teams_playing_today

# Run one a day in morning to check if there are any games today
def update_player_status():
    today_player_ids = []
    data = today_games()
    if data:
        for team in data:
            obj = Player.objects.filter(team=team)
            for player in obj:
                today_player_ids.append(player.id)
        update_player_status1(today_player_ids)

# Run once an hour if ^^^ today there are games
def update_player_status1(today_player_ids):
    for id in today_player_ids:        
        result = fetch_player_positions(id)
        
        athlete = result.get('athlete', {})

        if 'injuries' in athlete:
            status = athlete.get('injuries', [])
            for s in status:
                status = s.get('type', {}).get('name', '')
        else:
            status = 'Active'
        
        Player.objects.update_or_create(
        id=id,
        defaults={
            'status': status})




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
x = update_espn_data()


def update_stats():

    data = get_stats()