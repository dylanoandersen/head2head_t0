import os
import django
import requests
import pytz
from datetime import datetime

# Ensure Django settings are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")
#django.setup()  # Initializes Django (uncomment if required to load Django models)

from .espn_api import fetch_espn_data, get_game_stats, fetch_player_positions, get_stats
from .models import Player, Game, Player_Stats

team_id = [(1, 'Falcons'), (2, 'Bills'), (3, 'Bears'), (4, 'Bengals'), (5, 'Browns'), (6, 'Cowboys'), (7, 'Broncos'), (8, 'Lions'), (9, 'Packers'), (34, 'Texans'), (11, 'Colts'), (30, 'Jaguars'), (12, 'Chiefs'), (14, 'Rams'), (24, 'Chargers'), (15, 'Dolphins'), (16, 'Vikings'), (17, 'Patriots'), (18, 'Saints'), (19, 'Giants'), (20, 'Jets'), (13, 'Raiders'), (21, 'Eagles'), (23, 'Steelers'), (25, '49ers'), (26, 'Seahawks'), (27, 'Buccaneers'), (10, 'Titans'), (22, 'Cardinals'), (28, 'Commanders'), (33, 'Ravens'), (29, 'Panthers')]
team_dict = {name: id for id, name in team_id}

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
    data, id, game_time = today_games()  # Get today's games and team IDs
    if data:
        for team in data:
            obj = Player.objects.filter(team=team)  # Find players on the teams playing today
            for player in obj:
                today_player_ids.append(player.id)
    else:
        print('No games today')
    return today_player_ids, id, game_time

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
        for id in today_player_ids:
            players_team = Player.objects.get(id=id).team
            team_number = team_dict.get(players_team)
            stats = get_stats(ids, team_number, id)
            if 'error' in stats:
                continue
            else:
                extra_points_attempts=extra_points_made=fg_attempts=fg_made=fg_perc=kick_1_19=kick_20_29=kick_30_39=kick_40_49=kick_50 = 0
                competition = stats.get('splits', {}).get('categories', [])
                for cat in competition:
                    if cat.get('name', '') == 'passing':
                        passing_stats = cat.get('stats',[])
                        for passi in passing_stats:
                            if passi.get('name', '') == 'passingAttempts':
                                pass_att = passi.get('value', 0)
                            elif passi.get('name', '') == 'completions':
                                completions = passi.get('value', 0)
                            elif passi.get('name', '') == 'completionPct':
                                completions_perc = passi.get('value', 0)
                            elif passi.get('name', '') == 'passingYards':
                                pass_yards = passi.get('value', 0)
                            elif passi.get('name', '') == 'yardsPerCompletion':
                                avg_pass_yards_completions = passi.get('value', 0)
                            elif passi.get('name', '') == 'passingTouchdowns':
                                pass_tds = passi.get('value', 0)
                            elif passi.get('name', '') == 'interceptions':
                                ints = passi.get('value', 0)
                            elif passi.get('name', '') == 'sacks':
                                sacks = passi.get('value', 0)
                            elif passi.get('name', '') == 'passingFumbles':
                                passing_fumbles = passi.get('value', 0)
                    elif cat.get('name', '') == 'rushing':
                        rushing_stats = cat.get('stats', [])
                        for rush in rushing_stats:
                            if rush.get('name', '') == 'rushingAttempts':
                                carrys = rush.get('value', 0)
                            elif rush.get('name', '') == 'rushingYards':
                                rush_yards = rush.get('value', 0)
                            elif rush.get('name', '') == 'yardsPerRushAttempt':
                                avg_rush_yards_perCarry = rush.get('value', 0)
                            elif rush.get('name', '') == 'rushingTouchdowns':
                                rush_tds = rush.get('value', 0)
                            elif rush.get('name', '') == 'rushingFumbles':
                                rush_fumbles = rush.get('value', 0)
                    elif cat.get('name', '') == 'receiving':
                        receiving_stats = cat.get('stats', [])
                        for rec in receiving_stats:
                            if rec.get('name', '') == 'receptions':
                                catches = rec.get('value', 0)
                            elif rec.get('name', '') == 'receivingTargets':
                                targets = rec.get('value', 0)
                            elif rec.get('name', '') == 'receivingYards':
                                recieving_yards = rec.get('value', 0)
                            elif rec.get('name', '') == 'yardsPerReception':
                                avg_recieving_yards_perCatch = rec.get('value', 0)
                            elif rec.get('name', '') == 'receivingTouchdowns':
                                receiving_tds = rec.get('value', 0)
                            elif rec.get('name', '') == 'receivingFumbles':
                                receiving_fumbles = rec.get('value', 0)
                    elif cat.get('name', '') == 'kicking':
                        kicking_stats = cat.get('stats', [])
                        for kick in kicking_stats:
                            if kick.get('name', '') == 'fgfieldGoalsMade1_191_19':
                                kick_1_19 = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalsMade20_29':
                                kick_20_29 = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalsMade30_39':
                                kick_30_39 = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalsMade40_49':
                                kick_40_49 = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalsMade50':
                                kick_50 = kick.get('value', 0)
                            elif kick.get('name', '') == 'extraPointAttempts':
                                extra_points_attempts = kick.get('value', 0)
                            elif kick.get('name', '') == 'extraPointsMade':
                                extra_points_made = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalAttempts':
                                fg_attempts = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalPct':
                                fg_perc = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalsMade':
                                fg_made = kick.get('value', 0)
                
                receiving_fumbles = int(receiving_fumbles if receiving_fumbles else 0)
                rush_fumbles = int(rush_fumbles if rush_fumbles else 0)
                qb_fumbles = int(passing_fumbles if passing_fumbles else 0)

                if Player.objects.get(id=id).position == 'QB':
                    fum = qb_fumbles + rush_fumbles
                    fum = str(fum)
                    Player_Stats.objects.update_or_create(
                        id=id,
                        defaults={
                            'fumbles': fum
                        })
                elif Player.objects.get(id=id).position == 'RB' or Player.objects.get(id=id).position == 'K':
                    rush_fumbles = str(rush_fumbles)
                    Player_Stats.objects.update_or_create(
                        id=id,
                        defaults={
                            'fumbles': rush_fumbles
                        })
                elif Player.objects.get(id=id).position == 'WR' or Player.objects.get(id=id).position == 'TE':
                    receiving_fumbles = str(receiving_fumbles)
                    Player_Stats.objects.update_or_create(
                        id=id,
                        defaults={
                            'fumbles': receiving_fumbles
                        })
                Player_Stats.objects.update_or_create(
                    id=id,
                    game_id=ids,
                    defaults={
                        'pass_att': pass_att,
                        'completions': completions,
                        'completions_perc': completions_perc,
                        'pass_yards': pass_yards,
                        'avg_pass_yards_completions': avg_pass_yards_completions,
                        'pass_tds': pass_tds,
                        'ints': ints,
                        'sacks': sacks,
                        'catches': catches,
                        'targets': targets,
                        'avg_recieving_yards_perCatch': avg_recieving_yards_perCatch,
                        'receiving_yards': recieving_yards,
                        'receiving_tds': receiving_tds,
                        'carrys': carrys,
                        'rush_yards': rush_yards,
                        'avg_rush_yards_perCarry': avg_rush_yards_perCarry,
                        'rush_tds': rush_tds,
                        'kick_1_19': kick_1_19,
                        'kick_20_29': kick_20_29,
                        'kick_30_39': kick_30_39,
                        'kick_40_49': kick_40_49,
                        'kick_50': kick_50,
                        'fg_perc': fg_perc,
                        'fg_attempts': fg_attempts,
                        'fg_made': fg_made,
                        'extra_points_made': extra_points_made,
                        'extra_points_attempts': extra_points_attempts,
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
    game_times = []
    for games in Game.objects.all():
        date_string = games.date
        utc_time = datetime.strptime(date_string, "%Y-%m-%dT%H:%MZ")
        utc_time = utc_time.replace(tzinfo=pytz.UTC)
        central_time = utc_time.astimezone(pytz.timezone("US/Central"))
        today = datetime.now(pytz.timezone("US/Central")).date()
        if central_time.date() == today:
            teams_playing_ids.append(games.id)
            teams_playing_today.extend([games.home_team, games.away_team])
            time = central_time.time()
            game_times.append(time)

    time_objects = [datetime.strptime(game_times, "%H:%M:%S").time() for time in game_times]
    time_objects.sort()
    times = 0
    if time_objects:
        earliest_time = time_objects[0]
        earliest_time_str = earliest_time.strftime("%H:%M:%S")
        times = [earliest_time_str]


    return teams_playing_today, teams_playing_ids, times

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


