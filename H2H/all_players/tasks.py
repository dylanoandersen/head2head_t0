import os
import django
import requests
import pytz
from datetime import datetime

# Ensure Django settings are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")
# django.setup()  # Initializes Django (uncomment if required to load Django models)

from .espn_api import fetch_espn_data, get_game_stats, fetch_player_positions
from .models import Player, Game

# Updates ESPN player data once a year, ensuring the database has the latest active players
def update_espn_data():
    data = fetch_espn_data()  # Fetch player data from the ESPN API
    players = data["items"]  # Extract the list of players

    # Loop through players and update or create records for active players
    for player in players:
        Player.objects.update_or_create(
            id=player['id'],  # Use player ID as the primary key
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

# Updates player positions and team data by fetching additional information
def update_player_positions():
    for player in Player.objects.all():  # Loop through all players in the database
        result = fetch_player_positions(player.id)  # Fetch position and team details

        athlete = result.get('athlete', {})  # Get athlete data

        # Extract position, team, and status information
        position = athlete.get('position', {}).get('name', '')
        team = athlete.get('team', {}).get('name', '')
        location = athlete.get('team', {}).get('location', '')

        # Determine player status (active or not) and handle injuries if present
        if athlete.get('active', '') == True:
            if 'injuries' in athlete:
                status = athlete.get('injuries', [])
                for s in status:
                    status = s.get('type', {}).get('name', '')
            else:
                status = 'Active'
        if athlete.get('active', '') == False:  # Remove inactive players
            Player.objects.filter(id=player.id).delete()
            print("Player deleted")

        # Update or create player data with new details
        Player.objects.update_or_create(
            id=player.id,
            defaults={
                'status': status,
                'team': team,
                'location': location,
                'position': position
            }
        )
        print("Player position added")

# Runs daily to check if there are any games scheduled for today
def live_update():
    print("Running daily task... live_update")
    today_player_ids = []  # List to store player IDs for today's games
    data, id = today_games()  # Get today's games and team IDs
    if data:
        for team in data:
            obj = Player.objects.filter(team=team)  # Find players on the teams playing today
            for player in obj:
                today_player_ids.append(player.id)
    else:
        print('No games today')
    return today_player_ids, id

# Updates player status and game data once a minute if there are games today
def update_player_status1(today_player_ids, game_id):
    for ids in game_id:
        url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={ids}'
        response = requests.get(url)

        # Handle API response and log results
        if response.status_code == 200:
            print("✅ Successfully fetched data! Parsing response...")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return

        # Parse game data from the API
        response_data = response.json()
        drives = response_data.get('drives', {})
        plays_list = drives.get('current', []) if 'current' in drives else drives.get('previous', [])

        # Extract play-by-play details
        home_score, away_score, text = 0, 0, "No plays available"
        for play_data in reversed(plays_list):
            if 'plays' in play_data:
                plays = play_data['plays']
                if plays:
                    last_play = plays[-1]
                    away_score = last_play.get('awayScore', 0)
                    home_score = last_play.get('homeScore', 0)
                    text = last_play.get('text', 'N/A')
                    break

        # Update or create Game object with live data
        Game.objects.update_or_create(
            id=ids,
            defaults={
                'home_score': home_score,
                'away_score': away_score,
                'current_play': text
            }
        )

    # Update player statuses
    for id in today_player_ids:
        result = fetch_player_positions(id)
        athlete = result.get('athlete', {})
        status = 'Active'  # Default status
        if 'injuries' in athlete:
            status = athlete.get('injuries', [])[0].get('type', {}).get('name', '')

        Player.objects.update_or_create(
            id=id,
            defaults={'status': status}
        )

# Retrieves a list of teams playing today and their game IDs
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
            teams_playing_today.extend([games.home_team, games.away_team])
    return teams_playing_today, teams_playing_ids

# Updates game data for the 2024 season
def update_game_data():
    season_2024 = [2024, 2025]
    for year in season_2024:
        data = get_game_stats(year)
        events = data.get("events", [])
        for event in events:
            id = event.get("id", "")
            date = event.get("date", "")
            season_type = event.get("season", {}).get("slug", "")
            if event.get("season", {}).get("year", 0) != 2024:
                continue
            for competition in event.get("competitions", []):
                home_team, away_team, home_score, away_score = "", "", "", ""
                for competitor in competition.get("competitors", []):
                    if competitor.get("homeAway") == "home":
                        home_team = competitor.get("team", {}).get("displayName", "")
                        home_score = competitor.get("score", "")
                    else:
                        away_team = competitor.get("team", {}).get("displayName", "")
                        away_score = competitor.get("score", "")

                # Update or create Game data
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
                print("Game data added")
