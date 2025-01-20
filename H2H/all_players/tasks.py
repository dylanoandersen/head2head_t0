import os
import django
import requests
import pytz
from datetime import datetime

# Ensure Django settings are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")
#django.setup()  # Initializes Django

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

# Run one a day in morning to check if there are any games today
def live_update():
    print("Running daily task... live_update")
    today_player_ids = []
    data,id = today_games()
    if data:
        for team in data:
            obj = Player.objects.filter(team=team)
            for player in obj:
                today_player_ids.append(player.id)
    else:
        print('No games today')
    return today_player_ids, id


# Run once an hour if ^^^ today there are games
def update_player_status1(today_player_ids, game_id):
    for ids in game_id:
        print(ids)
        url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={ids}'
        response = requests.get(url)

        if response.status_code == 200:
            print("✅ Successfully fetched data! Parsing response...")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return  # Exit the function if the API call fails

        # Parse the JSON response
        response_data = response.json()

        # Check if 'current' exists in 'drivers', otherwise use 'previous'
        drives = response_data.get('drives', {})
        plays_list = drives.get('current', []) if 'current' in drives else drives.get('previous', [])

        # Initialize default values for home_score, away_score, and text
        home_score = 0
        away_score = 0
        text = "No plays available"

        # Traverse plays_list from the end
        for play_data in reversed(plays_list):
            # Look for the 'plays' key
            if 'plays' in play_data:
                plays = play_data['plays']  # Extract the plays list
                if plays:  # Ensure plays is not empty
                    # Get the last play in the plays list
                    last_play = plays[-1]
                    # Extract desired values
                    away_score = last_play.get('awayScore', 0)
                    home_score = last_play.get('homeScore', 0)
                    text = last_play.get('text', 'N/A')

                    break
                else:
                    print("nothing in plays")
            else:
                print("nothing named plays")

        # Update or create Game object
        Game.objects.update_or_create(
            id=ids,
            defaults={
                'home_score': home_score,
                'away_score': away_score,
                'current_play': text
            }
        )
        obj=Game.objects.get(id=ids)
        print(vars(obj))

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

def today_games():
    teams_playing_today = []
    teams_playing_ids = []

    for games in Game.objects.all():
        date_string = games.date  
        
        utc_time = datetime.strptime(date_string, "%Y-%m-%dT%H:%MZ")
        utc_time = utc_time.replace(tzinfo=pytz.UTC)
        central_time = utc_time.astimezone(pytz.timezone("US/Central"))

        today = datetime.now(pytz.timezone("US/Central")).date()

        if central_time.date() == today:
            teams_playing_ids.append(games.id)
            teams_playing_today.append(games.home_team)
            teams_playing_today.append(games.away_team)
            
    return teams_playing_today, teams_playing_ids

# Update daily
def update_game_data():
    season_2024 = [2024, 2025]
    for year in season_2024:
        data = get_game_stats(year)
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

