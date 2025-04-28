import os
import django
import requests
import pytz
import sys
import itertools
from django.db.models import F

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")
django.setup()  # Initializes Django (uncomment if required to load Django models)
from django.db import connection
from asgiref.sync import sync_to_async
import asyncio
from datetime import datetime, date, timedelta
from django.core.files.base import ContentFile
from User import models
from django.contrib.auth.models import User
import random

# Ensure Django settings are loaded

from all_players.espn_api import fetch_espn_data, get_game_stats, fetch_player_positions, get_stats, game_details, get_def_stats, get_pts_proj, get_totalYearly_proj, player_news, player_headshots, get_bye_teams
from all_players.models import Player, Game, Player_Stats, Player_News, Def_Stats
from User.models import League, Week

team_id = [(1, 'Falcons'), (2, 'Bills'), (3, 'Bears'), (4, 'Bengals'), (5, 'Browns'), (6, 'Cowboys'), (7, 'Broncos'), (8, 'Lions'), (9, 'Packers'), (34, 'Texans'), (11, 'Colts'), (30, 'Jaguars'), (12, 'Chiefs'), (14, 'Rams'), (24, 'Chargers'), (15, 'Dolphins'), (16, 'Vikings'), (17, 'Patriots'), (18, 'Saints'), (19, 'Giants'), (20, 'Jets'), (13, 'Raiders'), (21, 'Eagles'), (23, 'Steelers'), (25, '49ers'), (26, 'Seahawks'), (27, 'Buccaneers'), (10, 'Titans'), (22, 'Cardinals'), (28, 'Commanders'), (33, 'Ravens'), (29, 'Panthers')]
team_dict = dict(team_id)
nfl_teams = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders"
}

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
        if result == 1:
            print(player.id, " problem !!!!!!!!!")
            continue
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
            continue

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

def delete_positionsNotNeeded():
    for players in Player.objects.all():
        if players.position == 'Quarterback' or players.position == 'Running Back' or players.position == 'Wide Receiver' or players.position == 'Tight End' or players.position == 'Place kicker' or players.position == 'DEF':
            continue
        else:
            print("player position: ", players.position)
            players.delete()

# Updates game data for the 2024 season
def update_game_data():
    season_2024 = [2024, 2025]
    for year in season_2024:
        data = get_game_stats(year)
        events = data.get("events", [])
        for event in events:
            if event.get("season", {}).get("year", 0) != 2024:
                continue
            if event.get("season", {}).get("slug","") != 'regular-season':
                continue

            id = event.get("id", "")
            date = event.get("date", "")
            season_type = event.get("season", {}).get("slug", "")
            week = event.get("week",{}).get("number",0)

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
                        'week': week,
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_score': home_score,
                        'away_score': away_score
                    }
                )
                print("Game data added")
                
def total_yearlyProjection():
    data = get_totalYearly_proj()
    for d in data:
        name = d.get('Name','')
        first_name = name.split(" ")[0]

        playrz = Player.objects.filter(firstName = first_name)
        if playrz:
            for player in playrz:
                if player.lastName in name:
                    print(name)
                    proj = d.get('FantasyPointsDraftKings',0)
                    print(proj)
                    Player.objects.update_or_create(
                        id = player.id,
                        defaults={
                            'yearly_proj': proj
                        }
                    )
                else:
                    continue

def player_headshot():
    for player in Player.objects.all():
        result = player_headshots(player.id)
        
        if result == 1:
            continue
        headshot = result.get('headshot', {}).get('href', '')
        if headshot == '':
            continue

        Player.objects.update_or_create(
            id=player.id,
            defaults={
                'headshot': headshot
            }
        )

def team_bye():
    for i in range(1, 18):
        result = get_bye_teams(i)
        team_lst = []
        print(i)

        if result == 1:
            print('Error fetching bye teams')
            continue
        try:
            teams = result.get('teamsOnBye')
            if not teams:
                print('empty')
                continue

            print('teams: ', teams)
            for team in teams:
                url = team.get("$ref", "")
                print('the team:', team)
                print('url: ', url)

                response = requests.get(url).json()
                team_num = response.get('id')
                print('team num: ', team_num)
                team_num = int(team_num)
                team_name = team_dict[team_num]
                print('name: ', team_name)
                team_lst.append(team_name)

            print('team name list: ', team_lst)
            for teamz in team_lst:
                print(f"Processing team: {teamz}")

                players = Player.objects.filter(team=teamz)  # Get all players in the team
                print(f"Players found for {teamz}: {list(players)}")  # Print the player queryset

                for p in players:
                    print(f"Processing player: {p} (ID: {p.id}, Team: {p.team})")

                    try:
                        w = Player.objects.get(id=p.id)
                        print(f"Retrieved player from DB: {w} (ID: {w.id})")

                        # Attempt to update or create Player_Stats
                        Player_Stats.objects.create(
                            player=w,
                            firstName = w.firstName,
                            lastName = w.lastName,
                            week = i,
                            proj_fantasy = -1
                            
                        )
                        print('Player stats added')

                    except Player.DoesNotExist:
                        print(f"❌ Player with ID {p.id} does not exist!")
                    except Exception as e:
                        print(f"❌ Unexpected error: {e}")

        except:
            print("No teams on bye")
            continue

def total():
    target_fields = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLX', 'K', 'DEF']
    for le in League.objects.all():
        users = le.users.all()
        for user in users:
            score = 0
            try:
                team = models.Team.objects.get(author=user, league=le)
                for field in team._meta.get_fields():
                    if field.name in target_fields and getattr(team, field.name) != 'N/A':
                        week = Week.objects.get(id=1).week

                        player = Player.objects.get(id=getattr(team, field.name))

                        p = Player_Stats.objects.get(player=player, week=week)
                        score = score + p.total_fantasy_points

                ma = models.Matchup.objects.filter(league = le, week=week)
                for m in ma:
                    if m.team1 == user or m.team2 == user:
                        if m.team1 == user:
                            m.team1score = score
                        else:
                            m.team2score = score
                        m.save()
            except:
                continue
def weekly_update():
    week = Week.objects.get(id=1).week
    matchups = models.Matchup.objects.filter(week = week)
    for m in matchups:
        team = models.Team.objects.get(author=m.team1, league=m.league)
        team.points_for = m.team1score
        team.points_against = m.team2score
        team.save(update_fields=['points_for', 'points_against'])

        team = models.Team.objects.get(author=m.team2, league=m.league)
        team.points_for = m.team2score
        team.points_against = m.team1score
        team.save(update_fields=['points_for', 'points_against'])


    Week.objects.filter(id=1).update(week=F('week') + 1)
    
    for l in League.objects.all():
        teams = models.Team.objects.filter(league=l).order_by('-wins', '-points_for')

        for index, team in enumerate(teams, start=1):
            team.rank = index
            team.save(update_fields=['rank']) 

def matchUp_creation(lid):
    print('Creating matchups...')
    league = League.objects.get(id = lid)
    users = list(league.users.all())
    username = [user.username for user in users]
    print(username)
    if len(username) % 2 != 0:
        username.append(None)  # None represents a bye

    # Generate all unique unordered matchups
    all_matchups = list(itertools.combinations(username, 2))
    random.shuffle(all_matchups)

    used_matchups = set()
    rounds = []
    positions = ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLX", "K", "DEF"]


    while len(rounds) < 15:
        current_round = []
        players_used = set()

        for p1, p2 in all_matchups:
            match = tuple(sorted((p1, p2)))  # canonical form for unordered

            if match in used_matchups:
                continue
            if p1 in players_used or p2 in players_used:
                continue

            used_matchups.add(match)
            current_round.append(match)
            players_used.update([p for p in (p1,p2) if p is not None])

            if len(current_round) == len(username) // 2:
                break  # round is full

        if current_round:
            rounds.append(current_round)

        # If all matchups are exhausted, reshuffle and start reusing
        if len(used_matchups) == len(all_matchups):
            used_matchups = set()
            random.shuffle(all_matchups)

    # Save matchups to DB
    print(rounds)
    for week_num, week in enumerate(rounds, 1):
        for team1_id, team2_id in week:
            print('team1: ',team1_id,'team2: ', team2_id)
            # Handle bye matchups
            if team1_id is None or team2_id is None:
                real_team_id = team1_id or team2_id
                real_team = (User.objects.get(id=real_team_id))
                random_position = random.choice(positions)


                models.Matchup.objects.update_or_create(
                    league=league,
                    week=week_num,
                    team1=real_team,
                    team2=None,  # or a special ByeUser if your model requires it
                    defaults={
                        'team1score': 0,
                        'team2score': 0,
                        'position': random.choice(["QB", "RB", "WR", "TE", "K"])  # Assign random position

                        # maybe include 'is_bye': True if you track it
                    }
                )
            else:
                team1 = User.objects.get(username=team1_id)
                team2 = User.objects.get(username=team2_id)

                models.Matchup.objects.update_or_create(
                    league=league,
                    week=week_num,
                    team1=team1,
                    team2=team2,
                    defaults={
                        'team1score': 0,
                        'team2score': 0,
                        'position': random.choice(["QB", "RB", "WR", "TE", "K"])  # Assign random position

                    }
                )